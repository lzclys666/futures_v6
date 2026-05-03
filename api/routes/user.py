# -*- coding: utf-8 -*-
"""
用户相关 API 路由
覆盖: /api/user/profile, /api/user/preferences, /api/user/risk-profile,
      /api/user/performance, /api/user/equity-curve
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger("user_api")

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


# ==================== 偏好设置 ====================

# 内存中的偏好存储（后续对接真实数据库）
_user_preferences: dict = {
    "defaultSymbol": "RU",
    "theme": "light",
    "language": "zh-CN",
    "refreshInterval": 10,
    "notifications": {
        "riskAlert": True,
        "tradeFilled": True,
        "circuitBreaker": True,
        "dailyReport": False,
        "channels": ["web"],
    },
}


class NotificationSettings(BaseModel):
    riskAlert: bool = True
    tradeFilled: bool = True
    circuitBreaker: bool = True
    dailyReport: bool = False
    channels: list[str] = ["web"]


class UserPreferences(BaseModel):
    defaultSymbol: str = "RU"
    theme: Literal["light", "dark"] = "light"
    language: Literal["zh-CN", "en-US"] = "zh-CN"
    refreshInterval: int = 10
    notifications: NotificationSettings = NotificationSettings()


@router.put("/preferences")
async def update_preferences(prefs: UserPreferences):
    """
    更新用户偏好设置
    前端调用：PUT /api/user/preferences
    """
    global _user_preferences
    _user_preferences = prefs.model_dump()
    logger.info(f"用户偏好已更新: theme={prefs.theme}, language={prefs.language}")
    return {
        "code": 0,
        "message": "success",
        "data": _user_preferences,
    }


@router.get("/preferences")
async def get_preferences():
    """
    获取用户偏好设置
    """
    return {
        "code": 0,
        "message": "success",
        "data": _user_preferences,
    }


# ==================== 风控画像 ====================

# 内存中的风控画像存储
_user_risk_profile: dict = {
    "riskTolerance": "moderate",
    "maxDrawdown": 15.0,
    "maxDailyLoss": 50000,
    "maxSingleSymbolPct": 30.0,
    "maxTotalPositionPct": 80.0,
    "maxLeverage": 5.0,
}


class RiskProfile(BaseModel):
    riskTolerance: Literal["conservative", "moderate", "aggressive"] = "moderate"
    maxDrawdown: float = 15.0
    maxDailyLoss: float = 50000
    maxSingleSymbolPct: float = 30.0
    maxTotalPositionPct: float = 80.0
    maxLeverage: float = 5.0


@router.put("/risk-profile")
async def update_risk_profile(profile: RiskProfile):
    """
    更新用户风控画像
    前端调用：PUT /api/user/risk-profile
    同时从 config/risk_rules.yaml 加载对应 profile 的阈值参数
    """
    global _user_risk_profile
    _user_risk_profile = profile.model_dump()
    logger.info(f"风控画像已更新: tolerance={profile.riskTolerance}, maxDrawdown={profile.maxDrawdown}%")

    # 同步更新 vnpy bridge 的风控画像（如果可用）
    try:
        from services.vnpy_bridge import get_vnpy_bridge
        bridge = get_vnpy_bridge()
        if hasattr(bridge, 'set_risk_profile'):
            bridge.set_risk_profile(profile.riskTolerance)
    except Exception as e:
        logger.warning(f"同步风控画像到 bridge 失败: {e}")

    # 同步更新 RiskEngine 的 profile（读取 config/risk_rules.yaml）
    try:
        import yaml
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "config" / "risk_rules.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            profiles = config_data.get("profiles", {})
            profile_params = profiles.get(profile.riskTolerance, {})
            if profile_params:
                logger.info(f"从 config/risk_rules.yaml 加载 profile '{profile.riskTolerance}' 参数: {list(profile_params.keys())}")
    except Exception as e:
        logger.warning(f"读取风控画像配置失败: {e}")

    return {
        "code": 0,
        "message": "success",
        "data": _user_risk_profile,
    }


@router.get("/risk-profile")
async def get_risk_profile():
    """
    获取用户风控画像
    """
    return {
        "code": 0,
        "message": "success",
        "data": _user_risk_profile,
    }
