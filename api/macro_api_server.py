"""
宏观打分 API Server · V1.0
===========================
FastAPI 实现，打分数据来自 macro_scoring_engine。

接口清单：
  GET /api/macro/signal/{symbol}          → MacroSignal
  GET /api/macro/signal/all               → MacroSignal[]
  GET /api/macro/factor/{symbol}           → FactorDetail[]
  GET /api/macro/score-history/{symbol}   → ScoreHistory[]

启动：
  cd scripts
  python -m uvicorn macro_api_server:app --reload --port 8000

自测（浏览器或 curl）：
  http://127.0.0.1:8000/api/macro/signal/RU
  http://127.0.0.1:8000/api/macro/signal/all
  http://127.0.0.1:8000/api/macro/factor/RU
  http://127.0.0.1:8000/api/macro/score-history/RU?days=30
  http://127.0.0.1:8000/docs   ← Swagger UI
"""

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import date, datetime
from scipy.stats import pearsonr
import csv
import math

import asyncio
import sys
import logging
from pathlib import Path
import sys

# ===== Python Path 设置（关键：macro_engine 必须在 D:\futures_v6 之前）=====
# macro_engine/core/ 有真实实现（D:utures_v6\core\ 是 stub）
# 必须先插入 macro_engine，确保 core.analysis.ic_heatmap_service 等导入真实服务
sys.path.insert(0, str(Path(__file__).parent.parent / "macro_engine"))  # D:\futures_v6\macro_engine
sys.path.insert(0, str(Path(__file__).parent))        # D:\futures_v6\api\
sys.path.insert(0, str(Path(__file__).parent.parent)) # D:\futures_v6\

import macro_scoring_engine as engine

# 新增路由模块
from routes.vnpy import router as vnpy_router
from routes.trading import router as trading_router
from routes.risk import router as risk_router
from routes.user import router as user_router
from routes.position import router as position_router
from routes.ic_heatmap import router as ic_heatmap_router
from routes.signal import router as signal_router
from routes.circuit_breaker import router as circuit_breaker_router

# VNpyBridge 懒加载（避免启动时依赖 VNpy）
_vnpy_bridge = None

def get_vnpy_bridge():
    global _vnpy_bridge
    if _vnpy_bridge is None:
        # 尝试加载 PaperBridge
        try:
            from services.vnpy_bridge import bridge as paper_bridge
            logging.getLogger("macro_api").warning(f"DEBUG: class={paper_bridge.__class__.__name__}, module={paper_bridge.__class__.__module__}")
            logging.getLogger("macro_api").warning(f"DEBUG: paper_bridge={paper_bridge}, status={paper_bridge.status}, value={paper_bridge.status.value}")
            if paper_bridge.status.value == "running":
                _vnpy_bridge = paper_bridge
                logging.getLogger("macro_api").info("PaperBridge auto-loaded")
        except ImportError as e:
            logging.getLogger("macro_api").warning(f"DEBUG: ImportError {e}")
        except Exception as e:
            logging.getLogger("macro_api").warning(f"DEBUG: Exception {e}")
    return _vnpy_bridge

def set_vnpy_bridge(bridge):
    global _vnpy_bridge
    _vnpy_bridge = bridge

# ---------------------------------------------------------------------------
# Pydantic 模型（与字段契约严格对齐）
# ---------------------------------------------------------------------------

Direction = Literal["LONG", "NEUTRAL", "SHORT"]


class FactorDetail(BaseModel):
    """因子明细（字段契约 V1.0：snake_case）"""
    factor_code: str = Field(..., alias="factorCode", description="因子代码，如 RU_TS_ROLL_YIELD")
    factor_name: str = Field(..., alias="factorName", description="因子中文名")
    factor_direction: Literal["positive", "negative", "neutral"] = Field(
        ..., description="因子方向：positive（正向）/ negative（反向）/ neutral（中性）"
    )
    factor_value: float = Field(..., description="标准化后得分（-1 ~ 1），即 normalized_score")
    factor_weight: float = Field(..., ge=0, le=1, description="因子权重（0 ~ 1），来自 FACTOR_META")
    contribution: float = Field(..., description="因子贡献度 = factor_value × factor_weight")
    factor_ic: Optional[float] = Field(None, alias="factorIc", description="因子 IC（可选），即 ic_value")

    class Config:
        populate_by_name = True  # 允许用 Python 原字段名创建


class MacroSignal(BaseModel):
    """单品种宏观信号"""
    symbol: str
    compositeScore: float = Field(..., ge=-1, le=1, description="综合打分（-1 ~ 1）")
    direction: Direction
    updatedAt: str = Field(..., description="ISO8601 更新时间")
    factors: List[FactorDetail] = Field(default_factory=list)


class ScoreHistory(BaseModel):
    """历史打分记录"""
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    score: float = Field(..., ge=-1, le=1)
    direction: Direction


class AgDailySignal(BaseModel):
    """AG每日信号 CSV 输出模型"""
    signal_date: str = Field(..., description="信号日期 YYYY-MM-DD")
    symbol: str = Field(default="AG", description="品种代码")
    gold_silver_ratio: Optional[float] = Field(None, description="金银比原始值")
    composite_score: float = Field(..., ge=-1, le=1, description="综合打分（-1 ~ 1）")
    direction: Direction = Field(..., description="方向建议：LONG/SHORT/NEUTRAL")
    confidence_level: Literal["高", "中", "低"] = Field(..., description="置信度评级")
    signal_generated_at: str = Field(..., description="信号生成时间 ISO8601")


ConfidenceLevel = Literal["高", "中", "低"]


# ---------------------------------------------------------------------------
# 新增：IC/Paper Trading/Risk 数据模型
# ----------------------------------------------------------------------------

class ICMetrics(BaseModel):
    """IC指标数据"""
    symbol: str
    ic_mean: float = Field(..., description="IC均值（6年平均）")
    ic_ir: float = Field(..., description="IC IR（信息比率）")
    t_stat: float = Field(..., description="t统计量")
    ic_significant: bool = Field(..., description="IC是否统计显著（|t|>2）")
    sample_period: str = Field(..., description="样本区间")
    updated_at: str


class PositionDetail(BaseModel):
    """持仓明细"""
    symbol: str
    direction: Direction
    position_pct: float = Field(..., ge=0, le=100, description="持仓比例 %")
    lots: int = Field(0, description="手数")
    entry_price: Optional[float] = Field(None, description="开仓价")
    current_price: Optional[float] = Field(None, description="当前价")
    unrealized_pnl: Optional[float] = Field(0, description="浮动盈亏")


class PaperPositions(BaseModel):
    """Paper Trading 持仓数据"""
    date: str
    total_equity: float = Field(1_000_000, description="总资金（默认100万）")
    available_cash: float
    positions: List[PositionDetail] = Field(default_factory=list)
    total_position_pct: float = Field(0, description="总持仓比例 %")
    daily_pnl: float = Field(0, description="当日盈亏")
    daily_return: float = Field(0, description="当日收益率")
    current_drawdown: float = Field(0, description="当前回撤（负数）")
    max_drawdown: float = Field(0, description="历史最大回撤（负数）")


class RiskLevel(BaseModel):
    """单层风控状态"""
    level: str = Field(..., description="风控层级，如 L1/L2/L3/L4/L5")
    name: str = Field(..., description="风控名称")
    status: Literal["normal", "warning", "triggered", "正常", "告警", "触发"]
    value: Optional[str] = Field(None, description="当前值")
    threshold: Optional[str] = Field(None, description="阈值")
    message: Optional[str] = Field(None, description="状态说明")


class RiskStatus(BaseModel):
    """风控状态汇总"""
    date: str
    overall_status: Literal["normal", "warning", "triggered", "正常", "告警", "触发"]
    levels: List[RiskLevel] = Field(default_factory=list)
    equity: float
    drawdown: float
    drawdown_alert: float = Field(-0.15, description="回撤告警线")
    drawdown_stop: float = Field(-0.20, description="回撤止损线")
    drawdown_circuit: float = Field(-0.25, description="回撤熔断线")
    updated_at: str


def _score_to_confidence(score: float) -> ConfidenceLevel:
    """
    根据综合打分绝对值判断置信度等级。
    - HIGH: |score| >= 0.3
    - MEDIUM: 0.15 <= |score| < 0.3
    - LOW: |score| < 0.15
    """
    abs_score = abs(score)
    if abs_score >= 0.3:
        return "高"
    elif abs_score >= 0.15:
        return "中"
    else:
        return "低"


class ApiResponse(BaseModel):
    """统一响应包装"""
    code: int = Field(0, description="0=成功，404=品种不存在，500=服务器错误")
    message: str = Field("success")
    data: Optional[object] = None


# ---------------------------------------------------------------------------
# FastAPI App（必须在 middleware 之前创建）
# ---------------------------------------------------------------------------

app = FastAPI(
    title="宏观打分 API",
    description="期货宏观基本面打分引擎 V6.0 接口层",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 允许前端跨域（生产环境限制为配置的前端域名）
import os as _os
_cors_origins = _os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 注册路由模块
app.include_router(vnpy_router)
app.include_router(trading_router)
app.include_router(risk_router)
app.include_router(user_router)
app.include_router(position_router)
app.include_router(ic_heatmap_router)
app.include_router(signal_router)
app.include_router(circuit_breaker_router)




# ---------------------------------------------------------------------------
# Exception Handler：统一 HTTPException 响应格式
#   HTTPException → {"code": <int>, "message": <str>, "data": null}
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", exc.status_code)
        message = detail.get("message", str(detail))
    else:
        code = exc.status_code
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message, "data": None},
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _wrap(data):
    return {"code": 0, "message": "success", "data": data}


def _not_found(symbol: str):
    raise HTTPException(
        status_code=404,
        detail={"code": 404, "message": f"symbol not found: {symbol}"},
    )


# ---------------------------------------------------------------------------
# 接口 1：GET /api/macro/signal/all  （必须在 {symbol} 前面定义）
# ---------------------------------------------------------------------------

@app.get(
    "/api/macro/signal/all",
    response_model=ApiResponse,
    summary="查询全品种信号列表",
    tags=["信号"],
)
def get_all_signals():
    """
    返回所有上线品种的信号摘要列表（不含因子明细）。
    """
    data = engine.get_all_signals()
    return _wrap(data)


# ---------------------------------------------------------------------------
# 接口 2：GET /api/macro/signal/{symbol}
# ---------------------------------------------------------------------------

@app.get(
    "/api/macro/signal/{symbol}",
    response_model=ApiResponse,
    summary="查询单品种宏观信号",
    tags=["信号"],
)
def get_signal(symbol: str):
    """
    返回指定品种的综合打分信号，包含因子明细。
    """
    try:
        data = engine.get_latest_signal(symbol.upper())
    except KeyError:
        _not_found(symbol)

    return _wrap(data)


# ---------------------------------------------------------------------------
# 接口 3：GET /api/macro/factor/{symbol}
# ---------------------------------------------------------------------------

@app.get(
    "/api/macro/factor/{symbol}",
    response_model=ApiResponse,
    summary="查询品种因子明细",
    tags=["因子"],
)
def get_factor(symbol: str):
    """
    返回指定品种的全部因子明细列表。
    """
    try:
        data = engine.get_factor_details(symbol.upper())
    except KeyError:
        _not_found(symbol)

    return _wrap(data)


# ---------------------------------------------------------------------------
# 接口 4：GET /api/macro/score-history/{symbol}
# ---------------------------------------------------------------------------

@app.get(
    "/api/macro/score-history/{symbol}",
    response_model=ApiResponse,
    summary="查询历史打分序列",
    tags=["历史"],
)
def get_score_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=90, description="查询天数，默认30，最大90"),
):
    """
    返回指定品种最近 N 个交易日的历史打分序列。
    """
    try:
        data = engine.get_score_history(symbol.upper(), days=days)
    except KeyError:
        _not_found(symbol)

    return _wrap(data)


# ---------------------------------------------------------------------------
# 接口 5：GET /api/trading/positions  持仓看板
# ---------------------------------------------------------------------------

@app.get(
    "/api/trading/positions",
    response_model=ApiResponse,
    summary="查询当前持仓",
    tags=["交易"],
)
def get_positions():
    """
    返回当前所有持仓信息。
    如 CTP 未连接，返回空持仓列表 + 模拟资金数据。
    """
    bridge = get_vnpy_bridge()
    today = date.today().isoformat()

    if bridge is None:
        # VNpyBridge 未初始化，返回空持仓
        data = PaperPositions(
            date=today,
            total_equity=1_000_000,
            available_cash=1_000_000,
            positions=[],
            total_position_pct=0,
            daily_pnl=0,
            daily_return=0,
            current_drawdown=0,
            max_drawdown=0,
        )
        return _wrap(data.model_dump())

    # 从 VNpy 获取真实持仓
    raw_positions = bridge.get_positions()
    account = bridge.get_account()

    total_equity = account["balance"] if account else 1_000_000
    available_cash = account["available"] if account else total_equity

    positions = []
    total_lots = 0
    total_pnl = 0.0

    for pos in raw_positions:
        # 估算持仓比例（简化计算，实际需要合约乘数）
        position_value = pos["price"] * pos["volume"] * 10  # 假设乘数10
        position_pct = (position_value / total_equity * 100) if total_equity > 0 else 0

        positions.append(PositionDetail(
            symbol=pos["symbol"].split(".")[0],
            direction=pos["direction"],
            position_pct=round(position_pct, 2),
            lots=pos["volume"],
            entry_price=round(pos["price"], 2),
            current_price=round(pos["price"], 2),
            unrealized_pnl=round(pos["pnl"], 2),
        ))
        total_lots += pos["volume"]
        total_pnl += pos["pnl"]

    total_position_pct = sum(p.position_pct for p in positions)

    data = PaperPositions(
        date=today,
        total_equity=round(total_equity, 2),
        available_cash=round(available_cash, 2),
        positions=positions,
        total_position_pct=round(total_position_pct, 2),
        daily_pnl=round(total_pnl, 2),
        daily_return=round(total_pnl / total_equity, 4) if total_equity > 0 else 0,
        current_drawdown=0,
        max_drawdown=0,
    )
    return _wrap(data.model_dump())


@app.get(
    "/api/trading/risk-status",
    response_model=ApiResponse,
    summary="查询风控状态",
    tags=["交易"],
)
def get_risk_status():
    """返回当前风控状态汇总"""
    today = date.today().isoformat()

    bridge = get_vnpy_bridge()
    risk_levels = []
    if bridge and hasattr(bridge, 'main_engine') and bridge.main_engine and hasattr(bridge.main_engine, 'get_engine'):
        risk_engine = bridge.main_engine.get_engine("RiskManager")
        if risk_engine:
            for rule in risk_engine.get_rule_status():
                risk_levels.append(RiskLevel(
                    level=rule["level"],
                    name=rule["name"],
                    status="正常" if rule["enabled"] else "关闭",
                    value=str(rule["threshold"]),
                    threshold=str(rule["threshold"]),
                ))

    if not risk_levels:
        risk_levels = [
            RiskLevel(level="L1", name="单品种最大持仓", status="normal", value="10手", threshold="10手"),
            RiskLevel(level="L1", name="单日最大亏损", status="normal", value="5000", threshold="5000"),
            RiskLevel(level="L2", name="涨跌停限制", status="normal", value="-", threshold="-"),
            RiskLevel(level="L2", name="总持仓比例上限", status="normal", value="80%", threshold="80%"),
            RiskLevel(level="L2", name="单品种集中度上限", status="normal", value="30%", threshold="30%"),
            RiskLevel(level="L3", name="连续亏损次数限制", status="normal", value="3次", threshold="3次"),
            RiskLevel(level="L4", name="交易时间检查", status="normal", value="-", threshold="-"),
            RiskLevel(level="L4", name="资金充足性检查", status="normal", value="-", threshold="-"),
            RiskLevel(level="L5", name="宏观熔断", status="normal", value="-0.5", threshold="-0.5"),
        ]

    account = bridge.get_account() if bridge else None
    equity = account["balance"] if account else 1_000_000

    data = RiskStatus(
        date=today,
        overall_status="normal",
        levels=risk_levels,
        equity=equity,
        drawdown=0,
        drawdown_alert=-0.15,
        drawdown_stop=-0.20,
        drawdown_circuit=-0.25,
        updated_at=datetime.now().isoformat(),
    )
    return _wrap(data.model_dump())


@app.get("/api/trading/risk-rules", response_model=ApiResponse, tags=["交易"])
def get_risk_rules():
    """获取所有风控规则配置（11条规则，与RiskEngine一致）"""
    bridge = get_vnpy_bridge()
    if bridge and hasattr(bridge, 'main_engine') and bridge.main_engine and hasattr(bridge.main_engine, 'get_engine'):
        risk_engine = bridge.main_engine.get_engine("RiskManager")
        if risk_engine:
            return _wrap(risk_engine.get_rule_status())
    
    # VNpy未连接时返回默认规则列表（与vnpy.py一致）
    default_rules = [
        {"id": "R10", "name": "R10 宏观熔断", "description": "宏观评分<30禁止做多，>70禁止做空，±5滞后区间", "layer": "L1", "enabled": True, "status": "normal"},
        {"id": "R5",  "name": "R5 波动率异常过滤", "description": "ATR/价格超2倍均值→WARN，超3倍→BLOCK", "layer": "L1", "enabled": True, "status": "normal"},
        {"id": "R6",  "name": "R6 流动性检查", "description": "订单量<20日均量5%，<盘口深度30%", "layer": "L1", "enabled": True, "status": "normal"},
        {"id": "R8",  "name": "R8 交易时间检查", "description": "非交易时段禁止下单，集合竞价禁开仓", "layer": "L3", "enabled": True, "status": "normal"},
        {"id": "R3",  "name": "R3 涨跌停限制", "description": "开仓价触及涨跌停板拒绝委托", "layer": "L1", "enabled": True, "status": "normal"},
        {"id": "R9",  "name": "R9 资金充足性检查", "description": "可用资金≥冻结+预冻结+5%安全缓冲", "layer": "L3", "enabled": True, "status": "normal"},
        {"id": "R2",  "name": "R2 单日最大亏损限制", "description": "当日亏损≥权益2.5%或5000元→禁止开仓", "layer": "L2", "enabled": True, "status": "normal"},
        {"id": "R7",  "name": "R7 连续亏损暂停", "description": "连续亏损≥5次→暂停，连续盈利≥3次→恢复", "layer": "L2", "enabled": True, "status": "normal"},
        {"id": "R11", "name": "R11 处置效应监控", "description": "亏损持仓占比≥50%且反向开仓→WARN", "layer": "L2", "enabled": True, "status": "normal"},
        {"id": "R1",  "name": "R1 品种持仓限制(动态)", "description": "基于20日波动率动态调整持仓比例上限", "layer": "L3", "enabled": True, "status": "normal"},
        {"id": "R4",  "name": "R4 总保证金上限(分时段)", "description": "交易时段≤70%，收盘前15分钟≤60%", "layer": "L3", "enabled": True, "status": "normal"},
    ]
    return _wrap(default_rules)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 交易接口（对接 VNpyBridge）
# ---------------------------------------------------------------------------

@app.get("/api/trading/orders", response_model=ApiResponse, tags=["交易"])
def get_orders():
    """获取当日所有订单"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        return _wrap([])
    return _wrap(bridge.get_orders())


@app.get("/api/trading/trades", response_model=ApiResponse, tags=["交易"])
def get_trades():
    """获取当日所有成交"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        return _wrap([])
    return _wrap(bridge.get_trades())


@app.get("/api/trading/account", response_model=ApiResponse, tags=["交易"])
def get_account():
    """获取账户资金"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        return _wrap(None)
    return _wrap(bridge.get_account())


class OrderRequestModel(BaseModel):
    vt_symbol: str
    direction: Literal["LONG", "SHORT"]
    offset: Literal["OPEN", "CLOSE", "CLOSETODAY", "CLOSEYESTERDAY"]
    price: float
    volume: int


@app.post("/api/trading/order", response_model=ApiResponse, tags=["交易"])
def send_order(req: OrderRequestModel):
    """下单"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "VNpyBridge 未初始化"})
    vt_orderid = bridge.send_order(
        req.vt_symbol, req.direction, req.offset, req.price, req.volume
    )
    if not vt_orderid:
        raise HTTPException(status_code=500, detail={"code": 500, "message": "下单失败"})
    return _wrap({"vt_orderid": vt_orderid})


@app.delete("/api/trading/order/{vt_orderid}", response_model=ApiResponse, tags=["交易"])
def cancel_order(vt_orderid: str):
    """撤单"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        raise HTTPException(status_code=503, detail={"code": 503, "message": "VNpyBridge 未初始化"})
    success = bridge.cancel_order(vt_orderid)
    if not success:
        raise HTTPException(status_code=500, detail={"code": 500, "message": "撤单失败"})
    return _wrap({"cancelled": True})


# ---------------------------------------------------------------------------
# WebSocket 实时推送
# ---------------------------------------------------------------------------

@app.websocket("/ws/trading")
async def websocket_trading(websocket: WebSocket):
    await websocket.accept()
    bridge = get_vnpy_bridge()
    if bridge:
        # 确保 bridge 持有事件循环（用于 WS 推送）
        if bridge._event_loop is None:
            bridge._event_loop = asyncio.get_running_loop()
        bridge.register_ws_client(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                if bridge:
                    status = bridge.get_status()
                    await websocket.send_text(json.dumps({"type": "status", "data": status}))
            elif data == "positions":
                if bridge:
                    positions = bridge.get_positions()
                    await websocket.send_text(json.dumps({"type": "positions", "data": positions}))
    except WebSocketDisconnect:
        pass
    finally:
        if bridge:
            bridge.unregister_ws_client(websocket)


@app.get("/health", response_model=ApiResponse, tags=["系统"])
def health():
    bridge = get_vnpy_bridge()
    return _wrap({
        "status": "ok",
        "service": "macro-api",
        "version": "1.0.0",
        "vnpy_bridge": "connected" if bridge else "disconnected"
    })


@app.get("/api/health", response_model=ApiResponse, tags=["系统"])
def api_health():
    """
    健康检查（/api 前缀版本）
    与 /health 返回内容一致，供前端统一调用
    """
    return health()


@app.get("/api/vnpy/status", response_model=ApiResponse, tags=["交易"])
def vnpy_status():
    """获取 VNpy 引擎状态"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        return _wrap({
            "status": "stopped",
            "connected": False,
            "account": None,
            "positions_count": 0,
        })
    
    account = bridge.get_account()
    positions = bridge.get_positions()
    
    return _wrap({
        "status": "running",
        "connected": True,
        "account": account,
        "positions_count": len(positions),
    })


# ---------------------------------------------------------------------------
# VNpy WebSocket 集成（结构化连接管理 + 事件订阅）
# ---------------------------------------------------------------------------

def _ensure_event_loop():
    """确保 VNpyBridge 持有当前 asyncio 事件循环的引用"""
    bridge = get_vnpy_bridge()
    if bridge and bridge._event_loop is None:
        try:
            bridge._event_loop = asyncio.get_running_loop()
            logger = logging.getLogger("VNpyBridge")
            logger.info("Event loop captured for WebSocket push")
        except RuntimeError:
            pass


@app.on_event("startup")
async def startup_vnpy_ws():
    """启动时集成 VNpy WebSocket 服务"""
    bridge = get_vnpy_bridge()
    if bridge is None:
        return
    
    _ensure_event_loop()
    
    # 导入并启动结构化 WebSocket 服务
    from websocket.vnpy_ws import VNpyWebSocket, ConnectionManager
    
    global _vnpy_ws_manager
    _vnpy_ws_manager = VNpyWebSocket(bridge)
    await _vnpy_ws_manager.start(app)
    logging.getLogger("macro_api").info("VNpy WebSocket service started at /ws/vnpy")


@app.on_event("shutdown")
async def shutdown_vnpy_ws():
    """停止时清理 VNpy WebSocket 服务"""
    if _vnpy_ws_manager:
        await _vnpy_ws_manager.stop()
        logging.getLogger("macro_api").info("VNpy WebSocket service stopped")


_vnpy_ws_manager = None
