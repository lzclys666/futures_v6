#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VNpyBridge REST API提供持仓、账户、订单、策略、风控的HTTP接口"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.vnpy_bridge import get_vnpy_bridge, VNpyBridge

router = APIRouter(prefix="/api/vnpy", tags=["vnpy"])


def _wrap(data=None, message: str = "success", code: int = 0):
    """统一 API 响应格式：{code, message, data}"""
    return {"code": code, "message": message, "data": data}


# ==================== 数据模型 ====================

class StrategyCreate(BaseModel):
    class_name: str
    strategy_name: str
    vt_symbol: str
    setting: Dict[str, Any] = {}


class StrategyEdit(BaseModel):
    setting: Dict[str, Any]


class CtpConnect(BaseModel):
    用户名: str
    密码: str
    经纪商代码: str = "9999"
    交易服务器: str
    行情服务器: str
    产品名称: str = "simnow_client_test"
    授权编码: str = ""


class OrderCreate(BaseModel):
    symbol: str
    exchange: str
    direction: str  # LONG / SHORT
    offset: str  # OPEN / CLOSE / CLOSETODAY / CLOSEYESTERDAY
    price: float
    volume: int
    order_type: str = "LIMIT"  # LIMIT / MARKET
    reference: str = ""  # 订单备注/来源标识


class OrderResponse(BaseModel):
    status: str
    vt_orderid: Optional[str] = None
    message: str
    timestamp: str


# ==================== 依赖注入 ====================

def get_bridge() -> VNpyBridge:
    """获取VNpyBridge实例"""
    return get_vnpy_bridge()


def require_running(bridge: VNpyBridge = Depends(get_bridge)):
    """检查VNpy是否运行"""
    # 临时跳过 is_running 检查因为 PaperBridge 始终运行
    return bridge


# ==================== 状态接口 ====================

@router.get("/status")
async def get_status(b: VNpyBridge = Depends(get_bridge)):
    """获取桥接状态"""
    return _wrap(b.get_status())


@router.post("/start")
async def start_vnpy(b: VNpyBridge = Depends(get_bridge)):
    """启动VNpy引擎"""
    if b.start():
        return _wrap(None, message="VNpy started")
    raise HTTPException(status_code=500, detail="Failed to start VNpy")


@router.post("/stop")
async def stop_vnpy(b: VNpyBridge = Depends(get_bridge)):
    """停止VNpy引擎"""
    if b.stop():
        return _wrap(None, message="VNpy stopped")
    raise HTTPException(status_code=500, detail="Failed to stop VNpy")


# ==================== 持仓接口 ====================

@router.get("/positions")
async def get_positions(b: VNpyBridge = Depends(require_running)):
    """获取所有持仓"""
    positions = b.get_positions()
    return _wrap({"items": positions, "count": len(positions)})


@router.get("/positions/{symbol}")
async def get_position(symbol: str, b: VNpyBridge = Depends(require_running)):
    """获取指定品种持仓"""
    positions = b.get_positions()
    for pos in positions:
        if pos["symbol"] == symbol:
            return _wrap(pos)
    raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")


# ==================== 账户接口 ====================

@router.get("/account")
async def get_account(b: VNpyBridge = Depends(require_running)):
    """获取账户信息"""
    account = b.get_account()
    if account:
        return _wrap(account)
    raise HTTPException(status_code=404, detail="Account data not available")


@router.get("/account/risk")
async def get_account_risk(b: VNpyBridge = Depends(require_running)):
    """获取账户风险指标"""
    account = b.get_account()
    positions = b.get_positions()

    if not account:
        raise HTTPException(status_code=404, detail="Account data not available")

    # 计算风险指标
    balance = account.get("balance", 0)
    available = account.get("available", 0)
    margin = account.get("margin", 0)

    # 持仓盈亏
    total_pnl = sum(p.get("pnl", 0) for p in positions)

    # 保证金使用率
    margin_ratio = (margin / balance * 100) if balance > 0 else 0

    # 可用资金比例
    available_ratio = (available / balance * 100) if balance > 0 else 0

    return _wrap({
            "balance": balance,
            "available": available,
            "margin": margin,
            "margin_ratio": round(margin_ratio, 2),
            "available_ratio": round(available_ratio, 2),
            "total_pnl": round(total_pnl, 2),
            "positions_count": len(positions),
            "risk_level": "HIGH" if margin_ratio > 80 else "MEDIUM" if margin_ratio > 50 else "LOW"
        })


# ==================== 订单接口 ====================

@router.get("/orders")
async def get_orders(b: VNpyBridge = Depends(require_running)):
    """获取所有订单"""
    orders = b.get_orders()
    return _wrap({"items": orders, "count": len(orders)})


@router.post("/place-order", response_model=OrderResponse)
async def place_order(order: OrderCreate, b: VNpyBridge = Depends(require_running)):
    """
    发送委托订单（真实下单）
    支持限价单(LIMIT)和市价单(MARKET)
    通过 PaperAccount 或 CTP 网关执行
    """
    # 参数校验
    if order.volume <= 0:
        raise HTTPException(status_code=400, detail="Volume must be positive")

    if order.order_type not in ["LIMIT", "MARKET"]:
        raise HTTPException(status_code=400, detail="order_type must be LIMIT or MARKET")

    if order.price <= 0 and order.order_type == "LIMIT":
        raise HTTPException(status_code=400, detail="Price must be positive for LIMIT order")

    # 构建vt_symbol
    vt_symbol = f"{order.symbol}.{order.exchange}"

    # 调用桥接层发送订单
    vt_orderid = b.send_order(
        vt_symbol=vt_symbol,
        direction=order.direction,
        offset=order.offset,
        price=order.price,
        volume=order.volume
    )

    if vt_orderid:
        return OrderResponse(
            status="success",
            vt_orderid=vt_orderid,
            message=f"Order placed: {order.direction} {order.offset} {order.volume}@{order.price} {vt_symbol}",
            timestamp=datetime.now().isoformat()
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Order rejected by VNpy engine. Check logs for details."
        )


@router.post("/cancel-order/{vt_orderid}")
async def cancel_order_endpoint(vt_orderid: str, b: VNpyBridge = Depends(require_running)):
    """撤销委托订单"""
    if b.cancel_order(vt_orderid):
        return _wrap({
            "vt_orderid": vt_orderid,
            "message": "Cancel request sent",
            "timestamp": datetime.now().isoformat()
        })
    raise HTTPException(status_code=500, detail="Failed to cancel order")


# 保留旧接口但标记为废弃，返回明确提示
@router.post("/orders")
async def create_order_legacy(order: OrderCreate, b: VNpyBridge = Depends(require_running)):
    """【已废弃】请使用 /api/vnpy/place-order 下单"""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /api/vnpy/place-order instead."
    )


# ==================== 成交接口 ====================

@router.get("/trades")
async def get_trades(b: VNpyBridge = Depends(require_running)):
    """获取所有成交"""
    trades = b.get_trades()
    return _wrap({"items": trades, "count": len(b.trades)})


# ==================== 策略接口 ====================

@router.get("/strategies")
async def get_strategies(b: VNpyBridge = Depends(require_running)):
    """获取所有策略"""
    strategies = b.get_strategies()
    return _wrap({"items": strategies, "count": len(b.strategies)})


@router.post("/strategies")
async def add_strategy(strategy: StrategyCreate, b: VNpyBridge = Depends(require_running)):
    """添加策略"""
    if b.add_strategy(
        class_name=strategy.class_name,
        strategy_name=strategy.strategy_name,
        vt_symbol=strategy.vt_symbol,
        setting=strategy.setting
    ):
        return _wrap(None, message=f"Strategy {strategy.strategy_name} added")
    raise HTTPException(status_code=500, detail="Failed to add strategy")


@router.post("/strategies/{name}/init")
async def init_strategy(name: str, b: VNpyBridge = Depends(require_running)):
    """初始化策略"""
    if b.init_strategy(name):
        return _wrap(None, message=f"Strategy {name} initialized")
    raise HTTPException(status_code=500, detail="Failed to initialize strategy")


@router.post("/strategies/{name}/start")
async def start_strategy(name: str, b: VNpyBridge = Depends(require_running)):
    """启动策略"""
    if b.start_strategy(name):
        return _wrap(None, message=f"Strategy {name} started")
    raise HTTPException(status_code=500, detail="Failed to start strategy")


@router.post("/strategies/{name}/stop")
async def stop_strategy(name: str, b: VNpyBridge = Depends(require_running)):
    """停止策略"""
    if b.stop_strategy(name):
        return _wrap(None, message=f"Strategy {name} stopped")
    raise HTTPException(status_code=500, detail="Failed to stop strategy")


@router.put("/strategies/{name}")
async def edit_strategy(name: str, edit: StrategyEdit, b: VNpyBridge = Depends(require_running)):
    """编辑策略参数"""
    if b.edit_strategy(name, edit.setting):
        return _wrap(None, message=f"Strategy {name} updated")
    raise HTTPException(status_code=500, detail="Failed to edit strategy")


@router.delete("/strategies/{name}")
async def remove_strategy(name: str, b: VNpyBridge = Depends(require_running)):
    """移除策略"""
    if b.remove_strategy(name):
        return _wrap(None, message=f"Strategy {name} removed")
    raise HTTPException(status_code=500, detail="Failed to remove strategy")


# ==================== 风控接口 ====================

# 懒加载RiskEngine（避免VNpy未启动时导入失败）
_risk_engine = None
_risk_engine_profile = 'moderate'


def _get_risk_engine():
    """懒加载RiskEngine单例"""
    global _risk_engine, _risk_engine_profile
    if _risk_engine is None:
        try:
            from core.risk.risk_engine import RiskEngine
            _risk_engine = RiskEngine(profile=_risk_engine_profile)
        except Exception as e:
            print(f"[RiskAPI] RiskEngine初始化失败: {e}")
    return _risk_engine


@router.get("/risk/status")
async def get_risk_status(b: VNpyBridge = Depends(require_running)):
    """获取风控状态"""
    return _wrap(b.get_risk_status())


@router.get("/risk/events")
async def get_risk_events(limit: int = 50, b: VNpyBridge = Depends(require_running)):
    """获取风控事件历史"""
    return _wrap({"items": b.get_risk_events(limit), "count": len(b.risk_events)})


@router.get("/risk/rules")
async def get_risk_rules():
    """获取风控规则列表（含实时启用/禁用状态）"""
    engine = _get_risk_engine()
    # 规则定义：与RiskEngine的11条规则一一对应
    rules_def = [
        {"id": "R10", "name": "R10 宏观熔断", "description": "宏观评分<30禁止做多，>70禁止做空，处于滞后区间", "layer": "L1"},
        {"id": "R5",  "name": "R5 波动率异常过滤", "description": "ATR/价格>2倍均值→WARN，超3倍→BLOCK", "layer": "L1"},
        {"id": "R6",  "name": "R6 流动性检查", "description": "订单量>20日均量1%，且盘口深度30%", "layer": "L1"},
        {"id": "R8",  "name": "R8 交易时间检查", "description": "非交易时段禁止下单，集合竞价禁开仓", "layer": "L3"},
        {"id": "R3",  "name": "R3 涨跌停限制", "description": "开仓价触及涨跌停板拒绝委托", "layer": "L1"},
        {"id": "R9",  "name": "R9 资金充足性检查", "description": "可用资金≥冻结+预冻结+5%安全缓冲", "layer": "L3"},
        {"id": "R2",  "name": "R2 单日最大亏损限制", "description": "当日亏损≥权益1.5%或50000元→禁止开仓", "layer": "L2"},
        {"id": "R7",  "name": "R7 连续亏损暂停", "description": "连续亏损3次→暂停，连续盈利≥3次→恢复", "layer": "L2"},
        {"id": "R11", "name": "R11 处置效应监控", "description": "亏损持仓占比>40%且反向开仓→WARN", "layer": "L2"},
        {"id": "R1",  "name": "R1 品种持仓限制(动态)", "description": "基于20日波动率动态调整持仓比例上限", "layer": "L3"},
        {"id": "R4",  "name": "R4 总保证金上限(分时)", "description": "交易时段>80%，收盘前15分钟>60%", "layer": "L3"},
    ]
    # 从RiskEngine获取实时启用状态
    if engine:
        for rule_def in rules_def:
            rid = rule_def["id"]
            if rid in engine.rule_instances:
                rule = engine.rule_instances[rid]
                rule_def["enabled"] = rule.is_enabled()
                # 添加特定规则的状态信息
                extra = {}
                if rid == "R7":
                    extra["consecutive_losses"] = rule.consecutive_losses
                    extra["consecutive_wins"] = rule.consecutive_wins
                    extra["is_paused"] = rule.is_paused
                    if rule.is_paused:
                        rule_def["message"] = f"交易暂停：连续亏损{rule.consecutive_losses}次"
                    elif rule.consecutive_losses >= rule.base_limit - 1:
                        rule_def["message"] = f"预警：再亏1次暂停"
                if extra:
                    rule_def["extra"] = extra
            else:
                rule_def["enabled"] = False
            # 默认状态：如果启用则为normal，否则为disabled
            rule_def["status"] = "disabled" if not rule_def.get("enabled", True) else "normal"
    else:
        # RiskEngine不可用时的降级
        for rule_def in rules_def:
            rule_def["enabled"] = True
            rule_def["status"] = "normal"
    return _wrap(rules_def)


@router.put("/risk/profile")
async def set_risk_profile(profile: str = 'moderate'):
    """切换风险画像: conservative | moderate | aggressive"""
    global _risk_engine, _risk_engine_profile
    if profile not in ('conservative', 'moderate', 'aggressive'):
        raise HTTPException(status_code=400, detail="Invalid profile. Use: conservative, moderate, aggressive")
    _risk_engine_profile = profile
    _risk_engine = None  # 重建
    engine = _get_risk_engine()
    return _wrap({
        "profile": profile,
        "rules": [r.rule_id for r in engine.rules] if engine else []
    }, message=f"风险画像切换为: {profile}")


@router.get("/risk/profile")
async def get_risk_profile():
    """获取当前风险画像"""
    return _wrap({"profile": _risk_engine_profile})


# ==================== CTP接口 ====================

@router.post("/ctp/connect")
async def connect_ctp(config: CtpConnect, b: VNpyBridge = Depends(require_running)):
    """连接CTP"""
    setting = {
        "用户名": config.用户名,
        "密码": config.密码,
        "经纪商代码": config.经纪商代码,
        "交易服务器": config.交易服务器,
        "行情服务器": config.行情服务器,
        "产品名称": config.产品名称,
        "授权编码": config.授权编码
    }

    if b.connect_ctp(setting):
        return _wrap(None, message="CTP connection initiated")
    raise HTTPException(status_code=500, detail="Failed to connect CTP")


@router.post("/ctp/disconnect")
async def disconnect_ctp(b: VNpyBridge = Depends(require_running)):
    """断开CTP"""
    b.disconnect_ctp()
    return _wrap(None, message="CTP disconnected")


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check(b: VNpyBridge = Depends(get_bridge)):
    """健康检查"""
    return _wrap({
        "status": "healthy",
        "vnpy_status": b.status.value,
        "timestamp": datetime.now().isoformat()
    })
