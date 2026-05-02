# -*- coding: utf-8 -*-
"""
用户相关 API 路由
覆盖: /api/user/profile, /api/user/performance, /api/user/equity-curve
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/user", tags=["user"])


# ==================== 用户信息 ====================

class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    riskProfile: str  # conservative / moderate / aggressive
    preferredSymbols: list[str]
    createdAt: str


class UserProfileResponse(BaseModel):
    status: str
    data: UserProfile


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile():
    """
    用户信息 — 当前固定返回 Mock 数据（后续对接真实用户系统）
    """
    return UserProfileResponse(
        status="success",
        data=UserProfile(
            id="user_001",
            name="交易员小明",
            email="trader@example.com",
            riskProfile="moderate",
            preferredSymbols=["RB", "HC", "J", "JM"],
            createdAt="2026-01-15T08:00:00Z"
        )
    )


# ==================== 绩效摘要 ====================

class PerformanceSummary(BaseModel):
    totalTrades: int
    winRate: float
    avgWin: float
    avgLoss: float
    totalPnl: float
    sharpeRatio: float
    maxDrawdown: float
    period: str


class PerformanceResponse(BaseModel):
    status: str
    data: PerformanceSummary


@router.get("/performance")
async def get_performance(period: str = "monthly"):
    """
    绩效摘要
    """
    seed = hash(period) % 1000
    random.seed(seed)

    win_rate = random.uniform(0.42, 0.58)
    trades = random.randint(80, 200)

    return PerformanceResponse(
        status="success",
        data=PerformanceSummary(
            totalTrades=trades,
            winRate=round(win_rate, 4),
            avgWin=round(random.uniform(800, 2000), 2),
            avgLoss=round(random.uniform(-2000, -500), 2),
            totalPnl=round(random.uniform(-50000, 150000), 2),
            sharpeRatio=round(random.uniform(0.8, 2.5), 2),
            maxDrawdown=round(random.uniform(0.05, 0.18), 4),
            period=period
        )
    )


# ==================== 资金曲线 ====================

class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown: float


class EquityCurveResponse(BaseModel):
    status: str
    data: list[EquityPoint]


@router.get("/equity-curve")
async def get_equity_curve(days: int = 90):
    """
    资金曲线 — 每日权益 + 回撤
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    points = []
    equity = 500000.0
    peak = 500000.0
    random.seed(42)

    for i in range(days, -1, -1):
        d = datetime.now() - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")

        # 模拟权益变化
        change = random.gauss(500, 5000)
        equity = max(100000, equity + change)
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak > 0 else 0

        points.append(EquityPoint(
            date=date_str,
            equity=round(equity, 2),
            drawdown=round(drawdown, 4)
        ))

    return EquityCurveResponse(status="success", data=points)
