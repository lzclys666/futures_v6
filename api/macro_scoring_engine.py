"""
宏观打分引擎 · 轻量版 V1.0
==========================
为 API 层提供打分数据。

职责：
- 管理品种列表
- 返回当前综合打分 + 因子明细
- 返回历史打分序列

数据来源（V1.0）：
  - 优先读取 C:\futures_data\macro_signals\{symbol}_macro_daily_{YYYYMMDD}.csv
  - CSV 不存在时 fallback 到内存模拟数据（兼容开发环境）

接口（供 api_server.py 调用）：
  get_latest_signals()         → dict[symbol, MacroSignal]
  get_factor_details(symbol)    → list[FactorDetail]
  get_score_history(symbol, days) → list[ScoreHistory]
"""

import csv
import random
import math
import os
import sys
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional
import akshare as ak
import json

# 确保 core/risk 在 Python 路径中（用于风控状态查询）
_CORE_DIR = Path(r"D:\futures_v6\core")
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

# ---------------------------------------------------------------------------
# 因子元数据（单一配置源）
# ---------------------------------------------------------------------------
FACTOR_META: Dict[str, List[dict]] = json.load(
    open(r"D:\futures_v6\config\factor_meta.json", encoding="utf-8")
)

# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------
Direction = Literal["LONG", "NEUTRAL", "SHORT"]
FactorDirection = Literal["positive", "negative", "neutral"]

# ---------------------------------------------------------------------------
# 信号阈值（业务规则）
# ---------------------------------------------------------------------------
# composite_score（归一化综合评分）阈值：> LONG_THRESHOLD → LONG, < SHORT_THRESHOLD → SHORT
LONG_THRESHOLD = 0.12
SHORT_THRESHOLD = -0.12

# 历史打分天数限制
HISTORY_DAYS_MIN = 1
HISTORY_DAYS_MAX = 90

# 浮点零消除阈值（用于消除浮点负零 contribution 和方向判断）
_CONTRIB_ZERO_THRESHOLD = 1e-9

# ---------------------------------------------------------------------------
# CSV 路径配置
# ---------------------------------------------------------------------------
CSV_BASE_DIR = Path(r"D:\futures_v6\macro_engine\output")


def _csv_path(symbol: str, trade_date: str) -> Path:
    """
    构建 CSV 文件路径。
    trade_date: YYYYMMDD 格式
    示例：C:\\futures_data\\macro_signals\\RU_macro_daily_20260420.csv
    """
    return CSV_BASE_DIR / f"{symbol}_macro_daily_{trade_date}.csv"


def _find_latest_csv_date(symbol: str) -> Optional[str]:
    """
    查找指定品种最新的 CSV 日期（YYYYMMDD）。
    用于当日 CSV 不存在时 fallback 到最近可用数据。
    """
    prefix = f"{symbol.upper()}_macro_daily_"
    try:
        files = [f.name for f in CSV_BASE_DIR.iterdir() if f.is_file() and f.name.startswith(prefix)]
    except FileNotFoundError:
        return None
    dates = []
    DATE_PART_LENGTH = 8   # YYYYMMDD 固定8位
    for fname in files:
        try:
            date_part = fname.replace(prefix, "").replace(".csv", "")
            if len(date_part) == DATE_PART_LENGTH and date_part.isdigit():
                dates.append(date_part)
        except ValueError:
            continue
    if not dates:
        return None
    dates.sort(reverse=True)
    return dates[0]


def _trade_date_str(d: Optional[date] = None) -> str:
    """返回 YYYYMMDD 格式的日期字符串。"""
    if d is None:
        d = date.today()
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# CSV 读取函数
# ---------------------------------------------------------------------------

def _normalize_row(row: dict) -> dict:
    """
    统一 CSV 行字段名：snake_case → camelCase
    兼容 backfill (snake_case) 和 engine v1.0 (camelCase) 两套格式。
    """
    if "rowType" in row:  # 已经是 camelCase，无需处理
        return row
    # 从 snake_case 映射到 camelCase
    KEY_MAP = {
        "row_type": "rowType",
        "composite_score": "compositeScore",
        "factor_count": "factorCount",
        "updated_at": "updatedAt",
        "engine_version": "engineVersion",
        "factor_code": "factorCode",
        "factor_name": "factorName",
        "raw_value": "rawValue",
        "normalized_score": "normalizedScore",
        "weight": "weight",
        "contribution": "contribution",
        "factor_value": "factor_value",
        "contribution_polarity": "contribution_polarity",
        "ic_value": "icValue",
    }
    normalized = {}
    for k, v in row.items():
        normalized[KEY_MAP.get(k, k)] = v
    return normalized


def _read_csv_row(symbol: str, row_type: str, trade_date: Optional[str] = None) -> Optional[dict]:
    """
    从 CSV 读取指定品种 + 行类型的第一条记录。
    row_type: 'SUMMARY' 或 'FACTOR'
    trade_date: YYYYMMDD 格式，默认今天
    返回 dict 或 None（文件不存在时）
    """
    if trade_date is None:
        trade_date = _trade_date_str()

    csv_file = _csv_path(symbol.upper(), trade_date)
    if not csv_file.exists():
        return None

    # 尝试 utf-8-sig（带BOM）→ gbk → utf-8 顺序自动推断编码
    for enc in ["utf-8-sig", "gbk", "utf-8"]:
        try:
            with open(csv_file, newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("rowType", row.get("row_type", "")).strip().upper() == row_type.upper():
                        return _normalize_row(row)
            break
        except UnicodeDecodeError:
            continue
    return None


def _read_csv_factors(symbol: str, trade_date: Optional[str] = None) -> List[dict]:
    """
    从 CSV 读取指定品种的全部 FACTOR 行。
    """
    if trade_date is None:
        trade_date = _trade_date_str()

    csv_file = _csv_path(symbol.upper(), trade_date)
    if not csv_file.exists():
        return []

    factors = []
    # 尝试 utf-8-sig（带BOM）→ gbk → utf-8 顺序自动推断编码
    for enc in ["utf-8-sig", "gbk", "utf-8"]:
        try:
            with open(csv_file, newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("rowType", row.get("row_type", "")).strip().upper() == "FACTOR":
                        factors.append(_normalize_row(row))
            break
        except UnicodeDecodeError:
            continue
    return factors


# ---------------------------------------------------------------------------
# 品种元数据（仅用于 fallback 模式）
# ---------------------------------------------------------------------------



AVAILABLE_SYMBOLS = list(FACTOR_META.keys())

# ---------------------------------------------------------------------------
# US CPI 缓存（通胀预期因子数据）
# ---------------------------------------------------------------------------
_US_CPI_CACHE: Dict[str, float] = {}  # date_str -> cpi_yoy


def _load_us_cpi_cache() -> None:
    """加载美国CPI同比数据（月频，前向填充到日频）"""
    try:
        df = ak.macro_usa_cpi_monthly()
        # 列名: 日期, 前值, 今值, 预测值
        for _, row in df.iterrows():
            date_str = str(row.iloc[0])[:10]  # 取日期部分
            cpi_yoy = float(row.iloc[2])  # 今值 (CPI 同比)
            _US_CPI_CACHE[date_str] = cpi_yoy
    except Exception:
        pass  # 降级到随机值


def _get_us_cpi_yoy(trade_date: str) -> float:
    """获取指定日期的美国CPI同比，无数据时前向填充"""
    date_str = trade_date[:10]
    if date_str in _US_CPI_CACHE:
        return _US_CPI_CACHE[date_str]
    # 前向填充：找最近的一个可用日期
    sorted_dates = sorted(_US_CPI_CACHE.keys(), reverse=True)
    for d in sorted_dates:
        if d <= date_str:
            return _US_CPI_CACHE[d]
# 默认 US CPI 同比（akshare 不可用时的兜底值）
DEFAULT_US_CPI_YOY = 3.0


def _get_us_cpi_yoy(trade_date: str) -> float:
    """获取指定日期的美国CPI同比，无数据时前向填充"""
    date_str = trade_date[:10]
    if date_str in _US_CPI_CACHE:
        return _US_CPI_CACHE[date_str]
    # 前向填充：找最近的一个可用日期
    sorted_dates = sorted(_US_CPI_CACHE.keys(), reverse=True)
    for d in sorted_dates:
        if d <= date_str:
            return _US_CPI_CACHE[d]
    return DEFAULT_US_CPI_YOY


# 启动时加载 CPI 数据（已禁用，避免阻塞 startup）
# _load_us_cpi_cache()  # 懒加载，首次使用时才调用


def composite_to_direction(score: float) -> Direction:
    if score > LONG_THRESHOLD:
        return "LONG"
    elif score < SHORT_THRESHOLD:
        return "SHORT"
    else:
        return "NEUTRAL"


# ---------------------------------------------------------------------------
# Mock 数据生成（fallback 模式）
# ---------------------------------------------------------------------------
# Mock 参数常量
_MOCK_RANDOM_SEED = 20260420
_MOCK_SCORE_HASH_SALT = "macro_v1"
_MOCK_SCORE_RANGE = 1.6          # [-0.8, 0.8] = (hash%1000/1000) * 1.6 - 0.8
_MOCK_SCORE_MIN = -0.8
_MOCK_SCORE_MAX =  0.8
_MOCK_DRIFT_SIGMA = 0.03         # Brownian motion 标准差
_MOCK_MEAN_REVERT = 0.05        # 均值回归强度

random.seed(_MOCK_RANDOM_SEED)


def _init_score(symbol: str) -> float:
    """为每个品种分配一个启动分数（_MOCK_SCORE_MIN ~ _MOCK_SCORE_MAX之间，符号由 hash 决定）"""
    h = hash(symbol + _MOCK_SCORE_HASH_SALT)
    r = (h % 1000) / 1000.0
    return (r * _MOCK_SCORE_RANGE) + _MOCK_SCORE_MIN


_current_scores: Dict[str, float] = {s: _init_score(s) for s in AVAILABLE_SYMBOLS}

_factor_raw_values: Dict[str, Dict[str, float]] = {
    s: {f["factor_code"]: random.uniform(-1, 1) for f in FACTOR_META[s]}
    for s in AVAILABLE_SYMBOLS
}


def _drift(symbol: str) -> float:
    """每日漂移：Brownian motion σ=_MOCK_DRIFT_SIGMA + 均值回归"""
    noise = random.gauss(0, _MOCK_DRIFT_SIGMA)
    score = _current_scores.get(symbol, 0.0)
    pull = -score * _MOCK_MEAN_REVERT
    new_score = score + noise + pull
    return max(_MOCK_SCORE_MIN, min(_MOCK_SCORE_MAX, new_score))


def refresh_scores() -> None:
    """推进时间：所有品种分数游走一步（可由定时任务调用）"""
    for s in AVAILABLE_SYMBOLS:
        _current_scores[s] = _drift(s)


# ---------------------------------------------------------------------------
# 风控状态查询（集成 risk_engine 12 条规则）
# ---------------------------------------------------------------------------
_RISK_ENGINE = None


def _get_risk_engine():
    """懒加载全局风控引擎实例"""
    global _RISK_ENGINE
    if _RISK_ENGINE is None:
        try:
            from risk.risk_engine import RiskEngine
            _RISK_ENGINE = RiskEngine(profile='moderate')
        except Exception:
            _RISK_ENGINE = None
    return _RISK_ENGINE


def _get_risk_statuses(symbol: str, composite_score: Optional[float] = None) -> Dict[str, str]:
    """
    查询 12 条风控规则的当前状态。
    返回 dict，key 为 r1~r12，value 为 PASS/WARN/BLOCK。
    规则无法评估时默认 PASS。
    """
    # 默认全部 PASS
    statuses = {
        "r1_single_position": "PASS",
        "r2_continuous_profit": "PASS",
        "r3_price_limit": "PASS",
        "r4_total_position": "PASS",
        "r5_stop_loss": "PASS",
        "r6_max_drawdown": "PASS",
        "r7_trading_frequency": "PASS",
        "r8_trading_hours": "PASS",
        "r9_frozen_capital": "PASS",
        "r10_circuit_breaker": "PASS",
        "r11_disposition_effect": "PASS",
        "r12_cancel_limit": "PASS",
    }

    engine = _get_risk_engine()
    if engine is None:
        return statuses

    try:
        from risk.risk_engine import OrderRequest, RiskContext, RiskAction

        # 构建基础订单（用于规则检查）
        order = OrderRequest(
            symbol=symbol,
            exchange="SHFE",
            direction="LONG",
            offset="OPEN",
            price=0.0,
            volume=1,
        )

        # 构建上下文（宏观评分可用，其余数据缺失时规则自行降级）
        market_data = {}
        if composite_score is not None:
            # R10 宏观熔断使用 [0,100] 评分，composite_score 在 [-1,1]
            market_data["macro_score"] = (composite_score + 1) * 50

        context = RiskContext(
            account=None,
            positions={},
            market_data=market_data,
        )

        # 执行风控检查
        results = engine.check_order(order, context)

        # 规则 ID → 字段名映射
        RULE_TO_FIELD = {
            "R1": "r1_single_position",
            "R2": "r2_continuous_profit",
            "R3": "r3_price_limit",
            "R4": "r4_total_position",
            "R5": "r5_stop_loss",
            "R6": "r6_max_drawdown",
            "R7": "r7_trading_frequency",
            "R8": "r8_trading_hours",
            "R9": "r9_frozen_capital",
            "R10": "r10_circuit_breaker",
            "R11": "r11_disposition_effect",
        }

        for r in results:
            field = RULE_TO_FIELD.get(r.rule_id)
            if field:
                statuses[field] = r.action.value

        # R12（撤单次数限制）在 risk_engine.py 中无实现类，默认 PASS
        # 如后续实现，此处补充映射

    except Exception:
        pass  # 降级：全部 PASS

    return statuses


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def get_latest_signal(symbol: str, trade_date: Optional[str] = None) -> dict:
    """
    返回单个品种的 MacroSignal dict。
    
    优先从 CSV 读取（真实引擎数据），CSV 不存在时 fallback 到 mock。
    
    trade_date: YYYYMMDD 格式，默认今天
    """
    if symbol.upper() not in AVAILABLE_SYMBOLS:
        raise KeyError(f"Unknown symbol: {symbol}")

    symbol = symbol.upper()
    today_str = trade_date or _trade_date_str()

    # 尝试从 CSV 读取 SUMMARY 行
    summary_row = _read_csv_row(symbol, "SUMMARY", today_str)

    if summary_row is not None:
        # 真实数据路径
        # 直接使用 CSV SUMMARY 行的 composite_score 和 direction（数据生成时已正确计算）
        # 不重新计算，避免因子原始值 (normalized_score=0) 覆盖已算好的综合得分
        updated_at = summary_row["updatedAt"].strip()
        raw_score = float(summary_row.get("compositeScore", "").strip())
        composite_score = (raw_score - 0.5) * 2  # [0,1] → [-1,1]
        direction = summary_row.get("direction", "NEUTRAL").strip().upper()
        factors = _build_factor_details_from_csv(symbol, today_str, composite_score)
    else:
        # Fallback: 找最近可用的 CSV，不使用 _current_scores（避免 Brownian motion 漂移）
        latest_date = _find_latest_csv_date(symbol)
        if latest_date is not None:
            summary_row = _read_csv_row(symbol, "SUMMARY", latest_date)
            if summary_row is not None:
                updated_at = summary_row["updatedAt"].strip() + " (非今日数据)"
                raw_score = float(summary_row.get("compositeScore", "").strip())
                composite_score = (raw_score - 0.5) * 2  # [0,1] → [-1,1]
                direction = summary_row.get("direction", "NEUTRAL").strip().upper()
                factors = _build_factor_details_from_csv(symbol, latest_date, composite_score)
            else:
                composite_score = _current_scores[symbol]
                direction = composite_to_direction(composite_score)
                factors = _build_factor_details_from_mock(symbol, composite_score)
                updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
        else:
            composite_score = _current_scores[symbol]
            direction = composite_to_direction(composite_score)
            factors = _build_factor_details_from_mock(symbol, composite_score)
            updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    return {
        "symbol": symbol,
        "compositeScore": round(composite_score, 4),
        "direction": direction,
        "updatedAt": updated_at,
        "factors": factors,
    }


def get_all_signals(trade_date: Optional[str] = None) -> List[dict]:
    """
    返回所有上线品种的 MacroSignal list（不含因子明细）。
    优先从 CSV 读取 SUMMARY 行；CSV 不存在时用 mock。
    """
    today_str = trade_date or _trade_date_str()
    signals = []

    for symbol in AVAILABLE_SYMBOLS:
        if not FACTOR_META[symbol]:  # 跳过空因子品种
            continue

        summary_row = _read_csv_row(symbol, "SUMMARY", today_str)

        if summary_row is not None:
            updated_at = summary_row["updatedAt"].strip()
            raw_score = float(summary_row.get("compositeScore", "").strip())
            composite_score = (raw_score - 0.5) * 2  # [0,1] → [-1,1]
            direction = summary_row.get("direction", "NEUTRAL").strip().upper()
            factors = _build_factor_details_from_csv(symbol, today_str, composite_score)
        else:
            # Fallback: 找最近可用的 CSV，不使用 _current_scores（避免 Brownian motion 漂移）
            latest_date = _find_latest_csv_date(symbol)
            if latest_date is not None:
                summary_row = _read_csv_row(symbol, "SUMMARY", latest_date)
                if summary_row is not None:
                    updated_at = summary_row["updatedAt"].strip() + " (非今日数据)"
                    raw_score = float(summary_row.get("compositeScore", "").strip())
                    composite_score = (raw_score - 0.5) * 2  # [0,1] → [-1,1]
                    direction = summary_row.get("direction", "NEUTRAL").strip().upper()
                else:
                    composite_score = _current_scores[symbol]
                    direction = composite_to_direction(composite_score)
                    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
            else:
                composite_score = _current_scores[symbol]
                direction = composite_to_direction(composite_score)
                updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

        signals.append({
            "symbol": symbol,
            "compositeScore": composite_score,
            "direction": direction,
            "updatedAt": updated_at,
        })

    return signals


def get_factor_details(symbol: str, trade_date: Optional[str] = None) -> List[dict]:
    """
    返回品种的因子明细 list[FactorDetail]。
    优先从 CSV 读取 FACTOR 行；CSV 不存在时用 mock。
    """
    if symbol.upper() not in AVAILABLE_SYMBOLS:
        raise KeyError(f"Unknown symbol: {symbol}")

    symbol = symbol.upper()
    today_str = trade_date or _trade_date_str()

    # 尝试从 CSV 读取 FACTOR 行
    csv_factors = _read_csv_factors(symbol, today_str)

    if csv_factors:
        # 获取综合评分用于风控状态查询
        summary_row = _read_csv_row(symbol, "SUMMARY", today_str)
        cs = None
        if summary_row:
            try:
                raw_s = float(summary_row.get("compositeScore", "").strip())
                cs = (raw_s - 0.5) * 2
            except (ValueError, AttributeError):
                pass
        return _build_factor_details_from_csv(symbol, today_str, cs)
    else:
        cs = _current_scores.get(symbol.upper())
        return _build_factor_details_from_mock(symbol, cs)


def _build_factor_details_from_csv(symbol: str, trade_date: str, composite_score: Optional[float] = None) -> List[dict]:
    """
    从 CSV FACTOR 行构建因子明细列表。
    字段映射：CSV normalized_score → normalizedScore（API 字段名，与前端 FactorDetail 一致）
              direction 统一为 positive/negative/neutral
    
    注意：weight 和 direction 始终从 FACTOR_META 读取（IC 驱动调整后的最新值），
          CSV 中的 weight 可能已过期。contribution 使用新的 weight 重新计算。
    """
    # 建立 factor_code → FACTOR_META 映射（获取最新 weight 和 direction）
    meta_map = {f["factor_code"]: f for f in FACTOR_META[symbol]}

    factors = []
    for row in _read_csv_factors(symbol, trade_date):
        norm_score = float(row["normalizedScore"])
        # 消除浮点负零：-0.0 在 JSON 序列化后会变成 0，前端 comparison 会错误
        if norm_score == 0.0:
            norm_score = 0.0
        factor_code = row["factorCode"].strip()
        
        # 从 FACTOR_META 获取最新的 weight 和 direction（覆盖 CSV 中的旧值）
        meta = meta_map.get(factor_code, {})
        weight = meta.get("weight", float(row["weight"]))
        
        # contribution：使用新的 weight 重新计算
        contribution = norm_score * weight
        # 消除浮点负零 contribution
        if abs(contribution) < _CONTRIB_ZERO_THRESHOLD:
            contribution = 0.0
        if contribution > _CONTRIB_ZERO_THRESHOLD:
            direction = "positive"
        elif contribution < -_CONTRIB_ZERO_THRESHOLD:
            direction = "negative"
        else:
            direction = "neutral"

        # rawValue：CSV 有 rawValue 列则用，无则保留 None（前端依此判断数据可用性）
        raw_val_str = row.get("rawValue", "").strip()
        raw_value: Optional[float] = float(raw_val_str) if raw_val_str else None

        factors.append({
            "factorCode": factor_code,
            "factorName": row["factorName"].strip(),
            "direction": direction,
            "rawValue": raw_value,
            "normalizedScore": norm_score,
            "weight": weight,
            "contribution": round(contribution, 6),
            "factorIc": float(row["icValue"]) if row.get("icValue", "").strip() else None,
        })

    # 注入 12 条风控规则状态
    risk_statuses = _get_risk_statuses(symbol, composite_score)
    for f in factors:
        f.update(risk_statuses)

    return factors


def _build_factor_details_from_mock(symbol: str, composite_score: Optional[float] = None) -> List[dict]:
    """Fallback: 从内存 mock 数据构建因子明细。"""
    meta_list = FACTOR_META[symbol]
    results = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for fmeta in meta_list:
        code = fmeta["factor_code"]
        # AU_INFLATION_EXP 使用真实 US CPI 同比数据
        if code == "AU_INFLATION_EXP":
            raw = _get_us_cpi_yoy(today_str)
        else:
            raw = _factor_raw_values[symbol].get(code, 0.0)
        norm = math.tanh(raw)
        weight = fmeta["weight"]
        ic = round(random.uniform(-0.1, 0.1), 4)
        contribution = norm * weight
        # 消除浮点负零 contribution
        if abs(contribution) < _CONTRIB_ZERO_THRESHOLD:
            contribution = 0.0
        if contribution > _CONTRIB_ZERO_THRESHOLD:
            direction = "positive"
        elif contribution < -_CONTRIB_ZERO_THRESHOLD:
            direction = "negative"
        else:
            direction = "neutral"

        results.append({
            "factorCode": code,
            "factorName": fmeta["factor_name"],
            "direction": direction,
            "rawValue": raw,
            "normalizedScore": round(norm, 4),
            "weight": weight,
            "contribution": round(contribution, 6),
            "factorIc": ic,
        })

    # 注入 12 条风控规则状态
    risk_statuses = _get_risk_statuses(symbol, composite_score)
    for f in results:
        f.update(risk_statuses)

    return results


def get_score_history(symbol: str, days: int = 30) -> List[dict]:
    """
    返回历史打分序列 list[ScoreHistory]。
    days: 默认 30，最大 90。

    策略（与 get_latest_signal 完全一致）：
    - 有 CSV 的日期 → 读 CSV SUMMARY 行（真实值）
    - 无 CSV 的日期 → fallback 到最近可用 CSV
    - 真正无任何 CSV 时 → 用 _current_scores（极少，仅开发环境）
    """
    if symbol.upper() not in AVAILABLE_SYMBOLS:
        raise KeyError(f"Unknown symbol: {symbol}")

    days = min(max(days, HISTORY_DAYS_MIN), HISTORY_DAYS_MAX)
    today = date.today()
    today_str = _trade_date_str(today)          # YYYYMMDD
    today_display = today.strftime("%Y-%m-%d") # YYYY-MM-DD
    results = []

    def _get_score_for_date(sym: str, d_str: str, d_display: str) -> dict:
        """内部方法：获取指定日期的分值，逻辑与 get_latest_signal 完全一致"""
        summary_row = _read_csv_row(sym, "SUMMARY", d_str)
        if summary_row is not None:
            score = float(summary_row.get("compositeScore", "").strip())
            direction = composite_to_direction(score)
            label = ""
        else:
            # fallback：找最近可用 CSV
            latest_date = _find_latest_csv_date(sym)
            if latest_date is not None and latest_date != d_str:
                summary_row = _read_csv_row(sym, "SUMMARY", latest_date)
                if summary_row is not None:
                    score = float(summary_row.get("compositeScore", "").strip())
                    direction = composite_to_direction(score)
                    label = "(非今日)"
                else:
                    score = _current_scores[sym]
                    direction = composite_to_direction(score)
                    label = "(模拟)"
            else:
                score = _current_scores[sym]
                direction = composite_to_direction(score)
                label = "(模拟)"
        return {
            "date": d_display,
            "score": round(score, 4),
            "direction": direction,
            "label": label,
        }

    sym = symbol.upper()

    # 历史日期：从 (today - days) 到 yesterday
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y%m%d")
        d_display = d.strftime("%Y-%m-%d")
        results.append(_get_score_for_date(sym, d_str, d_display))

    # 今天
    today_entry = _get_score_for_date(sym, today_str, today_display)
    results.append(today_entry)

    return results
