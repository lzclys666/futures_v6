# core/scoring/weight_engine.py
"""
动态权重引擎 - 基于 IC (Information Coefficient) 的因子加权
计算每个因子与前瞻收益的 Pearson IC 均值，输出基于 IC 强度的动态权重。

与 validate_factor_ic.py 共用 IC 计算核心逻辑（compute_ic_series / compute_ic_metrics），
区别在于：
  - validate_factor_ic.py：从 CSV 文件读取因子数据（用于研究报告）
  - weight_engine.py：从 pit_data.db 读取因子观测值（用于实盘流水线）
"""

from typing import Dict, List, Optional
from datetime import date, timedelta
import sqlite3
import numpy as np
from scipy.stats import pearsonr


# ============ 全局参数 ============
IC_WINDOW = 60          # 滚动 IC 窗口（天）
FORWARD_N = 5           # 前瞻收益期（天）
MIN_PERIODS = 20        # 最少有效数据点
MIN_IC_WEIGHT = 0.02   # 因子最低权重


# ============ 数据库路径 ============
DB_PATH = r'D:\futures_v6\macro_engine\pit_data.db'


# ============ IC 计算核心（来自 validate_factor_ic.py） ============

def _compute_ic_series(factor_values: Dict[str, float],
                       forward_returns: Dict[str, float],
                       window: int = IC_WINDOW) -> Optional[Dict[str, float]]:
    """
    计算滚动 IC 序列（Pearson）
    IC(t) = corr(factor(0:t), ret(t:t+n))

    参数：
        factor_values: {date_str: factor_value} 升序
        forward_returns: {date_str: forward_return} 与 factor_values 日期对齐
        window: 滚动窗口大小

    Returns: {date_str: ic_value} 或 None
    """
    # 对齐：只保留两者都有的日期
    aligned = []
    for d in sorted(factor_values.keys()):
        fv = factor_values.get(d)
        rv = forward_returns.get(d)
        if fv is not None and rv is not None:
            try:
                if not (np.isnan(float(fv)) or np.isnan(float(rv))):
                    aligned.append((d, float(fv), float(rv)))
            except (TypeError, ValueError):
                continue

    if len(aligned) < MIN_PERIODS:
        return None

    ic_list = []
    n = len(aligned)

    for i in range(window, n):
        win = aligned[max(0, i - window + 1):i + 1]
        if len(win) < MIN_PERIODS:
            continue

        f_vals = np.array([w[1] for w in win])
        r_vals = np.array([w[2] for w in win])

        mask = ~(np.isnan(f_vals) | np.isnan(r_vals))
        if mask.sum() < MIN_PERIODS:
            continue

        try:
            corr, _ = pearsonr(f_vals[mask], r_vals[mask])
            if not np.isnan(corr):
                ic_list.append((aligned[i][0], corr))
        except Exception:
            continue

    return dict(ic_list) if ic_list else None


def _compute_ic_metrics(ic_dict: Dict[str, float]) -> Optional[Dict]:
    """计算 IC 统计指标"""
    if not ic_dict or len(ic_dict) < MIN_PERIODS:
        return None

    ic_vals = np.array(list(ic_dict.values()))
    ic_vals = ic_vals[~np.isnan(ic_vals)]

    if len(ic_vals) < MIN_PERIODS:
        return None

    return {
        'ic_mean': float(np.mean(ic_vals)),
        'ic_std': float(np.std(ic_vals)),
        'ir': float(np.mean(ic_vals) / np.std(ic_vals)) if np.std(ic_vals) > 0 else 0.0,
        'win_rate': float(np.mean(ic_vals > 0)),
        'count': len(ic_vals),
    }


# ============ 数据加载 ============

def _get_futures_close_series(symbol: str,
                               start_date: date,
                               end_date: date) -> Dict[str, float]:
    """
    从 pit_data.db 读取期货收盘价序列（按 trade_date 排列）
    OHLCV 表使用 trade_date（真实交易日期），不用 obs_date（入库日期）

    Returns: {trade_date_str: close_price} 升序
    """
    table_map = {
        'JM': 'jm_futures_ohlcv',
        'RU': 'ru_futures_ohlcv',
        'CU': 'cu_futures_ohlcv',
        'AL': 'al_futures_ohlcv',
        'ZN': 'zn_futures_ohlcv',
        'NI': 'ni_futures_ohlcv',
        'AU': 'au_futures_ohlcv',
        'AG': 'ag_futures_ohlcv',
        'RB': 'rb_futures_ohlcv',
        'HC': 'hc_futures_ohlcv',
        'M':  'm_futures_ohlcv',
        'Y':  'y_futures_ohlcv',
        'P':  'p_futures_ohlcv',
        'I':  'i_futures_ohlcv',
        'J':  'j_futures_ohlcv',
    }

    symbol_upper = symbol.upper()
    table = table_map.get(symbol_upper)

    if not table:
        return {}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 优先用 trade_date（真实行情日期），其次用 obs_date
        cursor.execute(f"""
            SELECT
                CASE WHEN trade_date IS NOT NULL AND trade_date != obs_date
                     THEN trade_date ELSE obs_date END AS price_date,
                close
            FROM {table}
            WHERE close IS NOT NULL
              AND ({('trade_date' if table == 'jm_futures_ohlcv' else 'trade_date')} >= ?
               OR obs_date >= ?)
            ORDER BY price_date ASC
        """, (start_date.isoformat(), start_date.isoformat()))

        rows = cursor.fetchall()
        conn.close()

        result = {}
        for price_date, close in rows:
            if price_date and close is not None:
                try:
                    result[str(price_date)] = float(close)
                except (TypeError, ValueError):
                    pass
        return result

    except Exception:
        return {}


def _get_factor_obs_window(factor_code: str,
                            symbol: str,
                            end_date: date,
                            window: int = 400) -> Dict[str, float]:
    """
    从 pit_factor_observations 读取因子历史窗口
    Returns: {obs_date_str: raw_value} 升序
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT obs_date, raw_value
            FROM pit_factor_observations
            WHERE factor_code = ?
              AND (symbol = ? OR symbol IS NULL OR symbol = '')
              AND obs_date <= ?
            ORDER BY obs_date ASC
            LIMIT ?
        ''', (factor_code, symbol, end_date.isoformat(), window))
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for obs_date, raw_value in rows:
            if raw_value is not None:
                try:
                    val = float(raw_value)
                    if not np.isnan(val):
                        result[str(obs_date)] = val
                except (TypeError, ValueError):
                    pass
        return result
    except Exception:
        return {}


def _compute_forward_returns(close_series: Dict[str, float],
                              forward_n: int = FORWARD_N) -> Dict[str, float]:
    """
    计算前瞻 N 日收益率（按 trade_date）
    ret(t+n) = close(t+n) / close(t) - 1
    返回映射到 ret 生效日期 t+n
    """
    if not close_series:
        return {}

    sorted_dates = sorted(close_series.keys())
    forward_ret = {}

    for i in range(len(sorted_dates) - forward_n):
        t = sorted_dates[i]
        t_n = sorted_dates[i + forward_n]
        p_t = close_series[t]
        p_tn = close_series[t_n]

        if p_t and p_tn and float(p_t) > 0:
            try:
                forward_ret[t_n] = (float(p_tn) - float(p_t)) / float(p_t)
            except (TypeError, ValueError):
                pass

    return forward_ret


# ============ 主类 ============

class WeightEngine:
    """
    动态权重引擎

    工作流程：
    1. 对每个因子，从 pit_data.db 读取历史窗口
    2. 对有期货价格数据的品种，计算因子 IC（因子 vs 前瞻收益）
    3. 无价格数据时，使用自IC（因子 vs 因子向前滞后）
    4. 输出基于 IC 均值绝对值的动态权重

    向后兼容：WeightNode 调用 calculate(symbol, factor_codes) → {fc: weight}
    """

    def __init__(self, db_path: str = None,
                 ic_window: int = IC_WINDOW,
                 forward_n: int = FORWARD_N,
                 min_ic_weight: float = MIN_IC_WEIGHT):
        self.db_path = db_path or DB_PATH
        self.ic_window = ic_window
        self.forward_n = forward_n
        self.min_ic_weight = min_ic_weight

        # Fallback 固定权重（数据不足时使用）
        self.default_weights = {
            "RU_TS_ROLL_YIELD": 0.15,
            "RU_STK_WARRANT": 0.15,
            "RU_INV_QINGDAO": 0.12,
        }

    def calculate(self, symbol: str,
                  factor_codes: List[str],
                  as_of_date: date = None,
                  **kwargs) -> Dict[str, float]:
        """
        计算动态权重

        参数：
            symbol: 品种代码（如 'RU'）
            factor_codes: 因子代码列表
            as_of_date: 计算日期（默认今天）

        返回：
            {factor_code: weight}，总和为 1.0
        """
        if as_of_date is None:
            as_of_date = date.today()

        start_date = as_of_date - timedelta(days=500)

        # 读取期货收盘序列（按 trade_date）
        close_series = _get_futures_close_series(symbol, start_date, as_of_date)
        forward_returns = _compute_forward_returns(close_series, self.forward_n)

        ic_means = {}

        for fc in factor_codes:
            # 读取因子窗口（按 obs_date）
            factor_window = _get_factor_obs_window(fc, symbol, as_of_date, window=400)

            if len(factor_window) < MIN_PERIODS:
                continue

            if forward_returns:
                # 标准 IC：因子值 vs 前瞻收益（按 trade_date 对齐）
                ic_series = _compute_ic_series(factor_window, forward_returns,
                                                 self.ic_window)
            else:
                # Fallback 自IC：因子 vs 因子向前滞后
                ic_series = self._compute_self_ic(factor_window, self.ic_window)

            if ic_series is None:
                continue

            metrics = _compute_ic_metrics(ic_series)
            if metrics is not None:
                ic_means[fc] = metrics['ic_mean']

        # 构建权重
        if not ic_means:
            return self._fallback_weights(factor_codes)

        # 基于 IC 均值绝对值分配权重
        abs_ic = {fc: abs(v) for fc, v in ic_means.items()}
        total = sum(abs_ic.values())

        if total <= 0:
            return self._fallback_weights(factor_codes)

        raw_weights = {fc: v / total for fc, v in abs_ic.items()}

        # 应用最低权重下限，并重新归一化
        weights = {}
        for fc in factor_codes:
            if fc in raw_weights:
                weights[fc] = max(raw_weights[fc], self.min_ic_weight)
            else:
                weights[fc] = self.min_ic_weight

        total_weights = sum(weights.values())
        weights = {k: v / total_weights for k, v in weights.items()}

        return weights

    def _compute_self_ic(self,
                          factor_window: Dict[str, float],
                          window: int) -> Optional[Dict[str, float]]:
        """
        自IC（无期货价格时的 fallback）：
        因子前瞻收益 = factor(t+n) / factor(t) - 1
        IC = corr(factor(t), factor_ret(t+n))
        """
        if len(factor_window) < window + self.forward_n + MIN_PERIODS:
            return None

        sorted_dates = sorted(factor_window.keys())
        fwd_factor = {}

        for i in range(len(sorted_dates) - self.forward_n):
            t = sorted_dates[i]
            t_n = sorted_dates[i + self.forward_n]
            v_t = factor_window[t]
            v_tn = factor_window[t_n]

            if v_t and v_tn and float(v_t) > 0:
                try:
                    fwd_factor[t_n] = (float(v_tn) - float(v_t)) / float(v_t)
                except (TypeError, ValueError):
                    pass

        return _compute_ic_series(factor_window, fwd_factor, window)

    def _fallback_weights(self, factor_codes: List[str]) -> Dict[str, float]:
        """所有 IC 计算失败时的 fallback：使用默认配置权重或均匀分配"""
        weights = {}
        for code in factor_codes:
            weights[code] = self.default_weights.get(code, 0.05)

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            n = len(factor_codes)
            weights = {k: 1.0 / n for k in factor_codes}

        return weights
