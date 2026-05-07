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


from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


from pydantic import BaseModel, Field


from typing import List, Literal, Optional


from datetime import date, datetime


from scipy.stats import pearsonr


import csv


import json


import math





import asyncio


import sys


import logging


from pathlib import Path





from api.schemas import FactorDetail


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
from routes.strategy import router as strategy_router
from api.routes.recon import router as recon_router
from services.signal_bridge import init_signal_ws





# VNpyBridge 懒加载（避免启动时依赖 VNpy）


_vnpy_bridge = None





def get_vnpy_bridge():


    """获取全局 VNpy Bridge 实例。


    优先使用 set_vnpy_bridge() 注入的实例（如由 app startup 事件注册），


    否则懒加载 services.vnpy_bridge.bridge（_BridgeProxy 会自动实例化 PaperBridge）。


    """


    global _vnpy_bridge


    if _vnpy_bridge is not None:


        return _vnpy_bridge


    # 懒加载：_BridgeProxy 内部直接实例化 PaperBridge，不再回调此函数


    try:


        from services.vnpy_bridge import get_vnpy_bridge


        _vnpy_bridge = get_vnpy_bridge()


        logging.getLogger("macro_api").info("PaperBridge auto-loaded via _BridgeProxy")


    except ImportError as e:


        logging.getLogger("macro_api").info(f"Bridge import failed: {e}")


    except Exception as e:


        logging.getLogger("macro_api").warning(f"Bridge load error: {e}")


    return _vnpy_bridge





def set_vnpy_bridge(bridge):


    global _vnpy_bridge


    _vnpy_bridge = bridge





# ---------------------------------------------------------------------------


# Pydantic 模型（与字段契约严格对齐）


# ---------------------------------------------------------------------------





Direction = Literal["LONG", "NEUTRAL", "SHORT"]








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
app.include_router(strategy_router)
app.include_router(recon_router)


# ---------------------------------------------------------------------------
# Auth middleware + login endpoint
# ---------------------------------------------------------------------------
try:
    from api.auth import create_auth_middleware, handle_login
    from pydantic import BaseModel as _BaseModel

    create_auth_middleware(app)

    class _LoginRequest(_BaseModel):
        api_key: str

    @app.post("/api/auth/login")
    async def auth_login(req: _LoginRequest):
        try:
            result = handle_login(req.api_key)
            return {"code": 0, "message": "success", "data": result}
        except ValueError as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail=str(e))

    logging.getLogger("macro_api").info("Auth middleware registered (API Key + JWT)")
except Exception as e:
    logging.getLogger("macro_api").warning(f"Auth middleware registration failed (non-fatal): {e}")













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


        return _wrap(data.model_dump(by_alias=True))





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


    return _wrap(data.model_dump(by_alias=True))
















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

# ---------------------------------------------------------------------------
# WebSocket 兼容路由：/events → 复用 /ws/trading 的逻辑
# 前猯 EventBusListener.ts 期望连接 ws://localhost:8000/events
# ---------------------------------------------------------------------------
@app.websocket("/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    bridge = get_vnpy_bridge()
    if bridge:
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









@app.get("/health", tags=["系统"])


def health():


    """


    Lightweight health check endpoint (no bridge dependency, < 100ms).


    Used by service_guardian and monitoring tools.


    """


    # Enhanced health check with sub-checks
    checks = {"database": "unknown", "signal_bridge": "unknown", "disk_space_mb": 0}
    overall = "ok"

    # Check 1: Database
    try:
        db_path = Path(r"D:\futures_v6\macro_engine\pit_data.db")
        if db_path.exists():
            checks["database"] = "ok"
        else:
            checks["database"] = "down"
            overall = "degraded"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall = "degraded"

    # Check 2: SignalBridge (check if recent CSV exists)
    try:
        output_dir = Path(r"D:\futures_v6\macro_engine\output")
        if output_dir.exists():
            csv_files = list(output_dir.glob("*.csv"))
            checks["signal_bridge"] = "ok" if csv_files else "no_data"
            if not csv_files:
                overall = "degraded"
        else:
            checks["signal_bridge"] = "down"
            overall = "degraded"
    except Exception as e:
        checks["signal_bridge"] = f"error: {e}"
        overall = "degraded"

    # Check 3: Disk space
    try:
        import shutil
        usage = shutil.disk_usage(r"D:\futures_v6")
        checks["disk_space_mb"] = int(usage.free / (1024 * 1024))
        if usage.free < 1024 * 1024 * 1024:  # < 1GB
            overall = "degraded"
    except Exception:
        checks["disk_space_mb"] = -1

    return {
        "status": overall,
        "service": "macro-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }








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


# ---------------------------------------------------------------------------
# SignalBridge 集成（宏观信号 CSV → WebSocket 推送）
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_signal_bridge():
    """启动 SignalBridge + StrategyRegistry"""
    # 1. SignalBridge
    try:
        init_signal_ws(app, use_mock=True)
        logging.getLogger("macro_api").info(
            "SignalBridge initialized (mock mode) → /ws/signal"
        )
    except Exception as e:
        logging.getLogger("macro_api").warning(
            f"SignalBridge init failed (non-fatal): {e}"
        )

    # 1.5 StrategyRegistry
    try:
        from core.strategy_registry import init_registry
        from pathlib import Path
        project_dir = Path(__file__).parent.parent
        registry = init_registry(
            strategy_dir=project_dir / "strategies",
            bindings_path=project_dir / "config" / "strategy_bindings.yaml",
            project_dir=project_dir,
        )
        logging.getLogger("macro_api").info(
            f"StrategyRegistry initialized: {len(registry.get_all_strategies())} strategies, "
            f"{len(registry.get_enabled_bindings())} enabled bindings"
        )
    except Exception as e:
        logging.getLogger("macro_api").warning(
            f"StrategyRegistry init failed (non-fatal): {e}"
        )

    # 1.7 AlertManager
    try:
        from api.alert import get_alert_manager
        mgr = get_alert_manager()
        logging.getLogger("macro_api").info(
            f"AlertManager initialized: {len(mgr._queue)} alerts loaded from DB"
        )
    except Exception as e:
        logging.getLogger("macro_api").warning(
            f"AlertManager init failed (non-fatal): {e}"
        )

    # 2. 风控 WebSocket 广播循环
    try:
        from routes.risk import _risk_broadcast_loop
        asyncio.create_task(_risk_broadcast_loop())
        logging.getLogger("macro_api").info(
            "Risk broadcast loop started → /ws/risk"
        )
    except Exception as e:
        logging.getLogger("macro_api").warning(
            f"Risk broadcast loop start failed (non-fatal): {e}"
        )


# ---------------------------------------------------------------------------
# WebSocket 风控推送端点 /ws/risk
# ---------------------------------------------------------------------------
@app.websocket("/ws/risk")
async def ws_risk_endpoint(websocket: WebSocket):
    """
    WebSocket 风控状态推送端点
    推送格式：{type: "risk_status_update", data: {overallStatus, rules, updatedAt}}
    支持命令：ping, get_status
    """
    from routes.risk import RiskConnectionManager, _get_risk_status_data, _risk_ws_manager

    await websocket.accept()
    _risk_ws_manager.add(websocket)
    try:
        # 连接时立即推送当前状态
        status_data = _get_risk_status_data()
        await websocket.send_text(json.dumps({
            "type": "risk_status_update",
            "data": status_data,
        }, ensure_ascii=False))

        # 保持连接，处理客户端命令
        while True:
            try:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                action = msg.get("action", "")

                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif action == "get_status":
                    status_data = _get_risk_status_data()
                    await websocket.send_text(json.dumps({
                        "type": "risk_status_update",
                        "data": status_data,
                    }, ensure_ascii=False))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                }))
    finally:
        _risk_ws_manager.remove(websocket)


# ---------------------------------------------------------------------------
# 前端静态文件服务（单端口部署：API + 前端同端口）
# ---------------------------------------------------------------------------
# 通过 SERVE_FRONTEND 环境变量控制是否挂载前端（默认 True）
# 开发时可设置 SERVE_FRONTEND=false 关闭，只用 Vite dev server
_SERVE_FRONTEND = _os.environ.get("SERVE_FRONTEND", "true").lower() in ("true", "1", "yes")
_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "futures_trading" / "frontend" / "dist"

if _SERVE_FRONTEND and _DIST_DIR.exists():
    # 1) SPA 路由兜底：非 /api/ 非 /ws/ 非 /events/ 非 /health 非 /docs 非 /redoc
    #    的 GET 请求 → 返回 index.html（React Router 客户端路由）
    #    必须在所有 API 路由之后注册，否则会拦截 API 请求
    @app.get("/{full_path:path}", tags=["前端"])
    async def serve_spa(full_path: str):
        """SPA 路由兜底：静态文件存在则返回文件，否则返回 index.html"""
        # 先检查是否对应 dist 中的真实文件
        file_path = _DIST_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # SPA fallback → index.html
        index_file = _DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"detail": "Frontend not built"}

    # 2) StaticFiles 挂载：处理根路径 / 和静态资源（/assets/ 等）
    #    html=True 使得访问 / 时自动返回 index.html
    #    必须在所有路由（包括 SPA catch-all）之后，作为最终兜底
    app.mount("/", StaticFiles(directory=str(_DIST_DIR), html=True), name="frontend")

    logging.getLogger("macro_api").info(
        f"Frontend static files served from {_DIST_DIR} (SERVE_FRONTEND=true)"
    )
elif _SERVE_FRONTEND:
    logging.getLogger("macro_api").warning(
        f"SERVE_FRONTEND=true but dist directory not found: {_DIST_DIR}. "
        f"Run frontend build first."
    )
else:
    logging.getLogger("macro_api").info("SERVE_FRONTEND=false, frontend serving disabled")


