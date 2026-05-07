"""
共享 Pydantic 模型 · 字段契约 V1.0
统一使用 camelCase alias，populate_by_name=True 允许 snake_case 输入。
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional

Direction = Literal["LONG", "NEUTRAL", "SHORT"]
FactorDirection = Literal["positive", "negative", "neutral"]


class FactorDetail(BaseModel):
    """因子明细（字段契约 V1.0：camelCase，与 API 实际响应完全对齐）"""
    model_config = ConfigDict(populate_by_name=True)

    factor_code: str = Field(..., alias="factorCode")
    factor_name: str = Field(..., alias="factorName")
    direction: FactorDirection = Field(..., alias="direction")
    raw_value: float = Field(..., alias="rawValue")
    normalized_score: float = Field(..., alias="normalizedScore")
    factor_weight: float = Field(..., ge=0, le=1, alias="weight")
    contribution: float = Field(..., alias="contribution")
    factor_ic: Optional[float] = Field(None, alias="factorIc")

    # 12 条风控规则状态（PASS/WARN/BLOCK）
    r1_single_position: Optional[str] = Field(None, alias="r1SinglePosition")
    r2_continuous_profit: Optional[str] = Field(None, alias="r2ContinuousProfit")
    r3_price_limit: Optional[str] = Field(None, alias="r3PriceLimit")
    r4_total_position: Optional[str] = Field(None, alias="r4TotalPosition")
    r5_stop_loss: Optional[str] = Field(None, alias="r5StopLoss")
    r6_max_drawdown: Optional[str] = Field(None, alias="r6MaxDrawdown")
    r7_trading_frequency: Optional[str] = Field(None, alias="r7TradingFrequency")
    r8_trading_hours: Optional[str] = Field(None, alias="r8TradingHours")
    r9_frozen_capital: Optional[str] = Field(None, alias="r9FrozenCapital")
    r10_circuit_breaker: Optional[str] = Field(None, alias="r10CircuitBreaker")
    r11_disposition_effect: Optional[str] = Field(None, alias="r11DispositionEffect")
    r12_cancel_limit: Optional[str] = Field(None, alias="r12CancelLimit")


class MacroSignal(BaseModel):
    """单品种宏观信号（字段契约 V1.0：对齐 API 实际响应）"""
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    composite_score: float = Field(..., ge=-1, le=1, alias="compositeScore")
    direction: Direction
    updated_at: str = Field(..., alias="updatedAt")
    factor_details: List[FactorDetail] = Field(default_factory=list, alias="factors")


class ScoreHistory(BaseModel):
    """历史打分记录"""
    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", alias="date")
    score: float = Field(..., ge=-1, le=1, alias="score")
    direction: Direction = Field(..., alias="direction")
