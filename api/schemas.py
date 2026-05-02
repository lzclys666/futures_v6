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
