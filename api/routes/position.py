# -*- coding: utf-8 -*-
"""
持仓相关 API 路由
覆盖: /api/position/disposition/{symbol}
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/position", tags=["position"])


class DispositionState(BaseModel):
    symbol: str
    holdingDays: int
    unrealizedPnl: float
    costBasis: float
    dispositionRatio: float  # 亏损持仓占比
    threshold: float
    status: str  # NORMAL / WARN / ALERT
    message: str


class DispositionResponse(BaseModel):
    status: str
    data: DispositionState


@router.get("/disposition/{symbol}", response_model=DispositionResponse)
async def get_disposition(symbol: str):
    """
    处置效应状态 — 监控亏损持仓行为偏差
    - holdingDays: 持仓天数（越长越倾向不止损）
    - dispositionRatio: 亏损持仓 / 总持仓（>50% 警示）
    - status: NORMAL / WARN / ALERT
    """
    # 从 VNpyBridge 获取真实持仓
    try:
        from services.vnpy_bridge import get_vnpy_bridge
        positions = get_vnpy_bridge().get_positions()
        position = next((p for p in positions if p.get("symbol") == symbol.upper()), None)
    except Exception:
        position = None

    if position:
        unrealized_pnl = position.get("unrealizedPnl", 0)
        avg_price = position.get("avgPrice", 0)
        volume = position.get("volume", 0)
        cost_basis = avg_price * volume
        holding_days = position.get("holdingDays", 3)

        # 处置效应：亏损持仓占比
        if cost_basis > 0:
            loss_ratio = abs(unrealized_pnl) / cost_basis if unrealized_pnl < 0 else 0
        else:
            loss_ratio = 0

        threshold = 0.5  # 50% 亏损占比阈值
        if loss_ratio > threshold:
            status = "ALERT"
            message = f"处置效应预警：{symbol} 亏损 {loss_ratio*100:.1f}%，建议评估是否止损"
        elif loss_ratio > threshold * 0.7:
            status = "WARN"
            message = f"注意：{symbol} 持仓亏损 {loss_ratio*100:.1f}%，关注处置效应倾向"
        else:
            status = "NORMAL"
            message = f"{symbol} 持仓正常"

        return DispositionResponse(
            status="success",
            data=DispositionState(
                symbol=symbol.upper(),
                holdingDays=holding_days,
                unrealizedPnl=round(unrealized_pnl, 2),
                costBasis=round(cost_basis, 2),
                dispositionRatio=round(loss_ratio, 4),
                threshold=threshold,
                status=status,
                message=message
            )
        )
    else:
        # 无持仓时返回 Mock 数据
        return DispositionResponse(
            status="success",
            data=DispositionState(
                symbol=symbol.upper(),
                holdingDays=0,
                unrealizedPnl=0.0,
                costBasis=0.0,
                dispositionRatio=0.0,
                threshold=0.5,
                status="NORMAL",
                message=f"{symbol} 当前无持仓"
            )
        )
