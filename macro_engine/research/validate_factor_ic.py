#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""
因子 IC 有效性验证框架
Factor IC Validation System

功能：
  1. IC 计算（Pearson + Spearman）
  2. IR 分析（IC均值/IC标准差）
  3. 滚动 IC（n日窗口）
  4. 因子衰减分析（持有期 vs IC 强度）
  5. t 统计量显著性检验
  6. 因子相关性矩阵
  7. Schmidt 正交化（去除共线性）
  8. 动态 IC 加权
  9. 多重检验校正（Bonferroni / FDR）
  10. 分层回测（分层验证 IC 稳定性）

用法：
  python validate_factor_ic.py --symbol CU --factors all --start 2020-01-01
  python validate_factor_ic.py --symbol CU --factors ZN_LME_STOCK,ZN_TC --start 2020-01-01
  python validate_factor_ic.py --symbol all --factors shared --start 2020-01-01

数据输入路径：
  str(MACRO_ENGINE)/data/crawlers/
"""

import os
import sys
import warnings
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np

# Windows console UTF-8 fix
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr, ttest_1samp
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression

warnings.filterwarnings('ignore')

# ============ 路径配置 ============
BASE_PATH = Path(r'D:\futures_v6\macro_engine\data\crawlers')
REPORT_PATH = Path(r'D:\futures_v6\macro_engine\research\reports')
REPORT_PATH.mkdir(parents=True, exist_ok=True)

# ============ 全局参数 ============
ROLLING_WINDOW = 60       # 滚动 IC 窗口（天）
FORWARD_DAYS = [1, 5, 10, 20]  # 前瞻收益期（天）
MIN_PERIODS = 30          # 最少有效数据点
SIGNIFICANCE_LEVEL = 0.05  # 显著性水平

# ============ IC 阈值（SOUL.md 标准） ============
IC_MIN = 0.02    # 最低标准
IC_GOOD = 0.05   # 良好标准
IC_EXCELLENT = 0.08  # 优秀标准
IR_MIN = 0.3     # IR 最低标准
IR_GOOD = 0.5    # IR 良好标准
T_STAT_MIN = 2.0  # t 统计量最低标准

# ============ 因子注册表 ============
# 格式: {因子代码: {name, symbol, source, direction, type}}
FACTOR_REGISTRY = {
    # === Phase 1: 宏观因子（已验证有效）===
    'USD_CNY_SPOT': {
        'name': '美元兑人民币即期汇率',
        'symbol': 'ALL',
        'source': 'AKShare/央行',
        'direction': -1,  # 汇率↑ → 大宗商品偏空（以人民币计价）
        'type': 'macro',
        'path': '_shared/daily/USD_CNY_spot.csv',
        'field': 'usd_cny',
        'comment': 'Phase 1 宏观因子 - 已验证有效（→AU IC=-0.146, →AG IC=-0.191, →CU IC=-0.158）'
    },
    'WTI_SPOT': {
        'name': 'WTI原油现货价',
        'symbol': 'ALL',
        'source': 'AKShare/FRED',
        'direction': 1,
        'type': 'macro',
        'path': '_shared/daily/Brent_crude.csv',
        'field': 'wti_spot_usd_bbl',
        'comment': 'Phase 1 宏观因子 - 已验证有效（10日IC=0.054）'
    },
    'CN_10Y_BOND': {
        'name': '中国10年期国债收益率',
        'symbol': 'ALL',
        'source': 'AKShare/bond_zh_us_rate',
        'direction': -1,  # 利率↑ → 经济偏紧 → 大宗商品偏空
        'type': 'macro',
        'path': '_shared/daily/CN_US_bond_yield_full.csv',
        'field': 'cn_10y',
        'comment': 'Phase 1 宏观因子 - 已验证有效（→AU IC=-0.068）'
    },
    # === Phase 4: 共用宏观因子 ===
    'USD_CNY_SPOT': {
        'name': '美元兑人民币即期汇率',
        'symbol': 'ALL',
        'source': 'AKShare/央行',
        'direction': -1,  # 汇率↑ → 大宗商品偏空（以人民币计价）
        'type': 'macro',
        'path': '_shared/daily/USD_CNY_spot.csv',
        'field': 'usd_cny',
        'comment': 'Phase 4 已完成采集（6年+历史）'
    },
    'WTI_SPOT': {
        'name': 'WTI原油现货价',
        'symbol': 'ALL',
        'source': 'AKShare/FRED',
        'direction': 1,
        'type': 'macro',
        'path': '_shared/daily/Brent_crude.csv',
        'field': 'wti_spot_usd_bbl',
        'comment': 'Phase 4 已完成采集（6年+历史）'
    },
    # === Phase 3: 品种因子（示例） ===
    'ZN_LME_STOCK': {
        'name': 'LME锌库存',
        'symbol': 'ZN',
        'source': 'AKShare/futures_inventory_em',
        'direction': -1,  # 库存↑ → 偏空
        'type': 'inventory',
        'path': None,  # 待采集
        'comment': 'Phase 3 v2.0 - ZN T1'
    },
    'ZN_FUT_CLOSE': {
        'name': '沪锌期货收盘价',
        'symbol': 'ZN',
        'source': 'AKShare/futures_main_sina',
        'direction': 1,
        'type': 'price',
        'path': None,  # 待采集（AKShare实时）
        'comment': 'Phase 3 v2.0 - ZN T1'
    },
    'AU_SPOT_SGE': {
        'name': 'SGE黄金现货价',
        'symbol': 'AU',
        'source': 'AKShare/spot_golden_benchmark_sge',
        'direction': 1,
        'type': 'price',
        'path': None,
        'comment': 'Phase 3 v2.0 - AU T1'
    },
    'AU_FUT_CLOSE': {
        'name': '沪金期货收盘价',
        'symbol': 'AU',
        'source': 'AKShare/futures_main_sina',
        'direction': 1,
        'type': 'price',
        'path': None,
        'comment': 'Phase 3 v2.0 - AU T1'
    },
    'AG_FUT_CLOSE': {
        'name': '沪银期货收盘价',
        'symbol': 'AG',
        'source': 'AKShare/futures_main_sina',
        'direction': 1,
        'type': 'price',
        'path': None,
        'comment': 'Phase 3 v2.0 - AG T1'
    },
    'HC_PMI_MFG': {
        'name': '中国制造业PMI',
        'symbol': 'HC',
        'source': 'AKShare/macro_china_pmi',
        'direction': 1,  # PMI↑ → 热卷需求↑ → 偏多
        'type': 'macro',
        'path': None,
        'comment': 'Phase 3 v2.0 - HC T2'
    },
    'RB_SPD_RB_HC': {
        'name': '螺纹钢-热卷价差',
        'symbol': 'RB',
        'source': 'AKShare计算',
        'direction': 1,  # RB-HC↑ → 螺纹相对偏强
        'type': 'spread',
        'path': None,
        'comment': 'Phase 3 v2.0 - RB T1'
    },
}


# ============ 数据加载模块 ============

def load_factor_data(factor_code, start_date=None, end_date=None):
    """
    加载单个因子数据
    Returns: pd.Series (index=date, values=factor_value)
    """
    if factor_code not in FACTOR_REGISTRY:
        raise ValueError(f'未知因子代码: {factor_code}')

    fdef = FACTOR_REGISTRY[factor_code]
    path = fdef.get('path')
    field = fdef.get('field', 'close')

    if path is None:
        # 数据尚未采集，返回占位符
        return None

    full_path = BASE_PATH / path
    if not full_path.exists():
        print(f'  [WARN] 文件不存在: {full_path}')
        return None

    try:
        df = pd.read_csv(full_path, parse_dates=['date'], index_col='date')
        series = df[field].dropna()

        if start_date:
            series = series[series.index >= start_date]
        if end_date:
            series = series[series.index <= end_date]

        series.name = factor_code
        return series

    except Exception as e:
        print(f'  [ERROR] 加载 {factor_code} 失败: {e}')
        return None


def compute_forward_return(price_series, forward_n):
    """
    计算前瞻N日收益率
    ret(t) = price(t+n) / price(t) - 1
    """
    ret = price_series.pct_change(forward_n).shift(-forward_n)
    return ret


def get_price_series(symbol, start_date, end_date):
    """
    获取期货价格序列（主力连续合约收盘价）
    优先从本地 CSV 读取（已采集数据），若无则通过 AKShare 获取
    """
    import os as _os

    # 先尝试从本地 CSV 读取
    local_paths = [
        BASE_PATH / symbol / 'daily' / f'{symbol}_fut_close.csv',
        BASE_PATH / symbol / 'daily' / f'{symbol}_spot_price.csv',
        BASE_PATH / symbol / 'daily' / f'{symbol}_close.csv',
    ]

    for p in local_paths:
        if p.exists():
            try:
                df = pd.read_csv(p, parse_dates=['date'], index_col='date')
                # 找收盘价列
                close_col = 'close' if 'close' in df.columns else df.columns[0]
                series = df[close_col].dropna()
                if start_date:
                    series = series[series.index >= start_date]
                if end_date:
                    series = series[series.index <= end_date]
                print(f'  [local CSV] {symbol} futures close: {len(series)} rows')
                return series
            except Exception:
                pass

    # AKShare fallback
    try:
        import akshare as ak
        symbol_map = {
            'CU': 'CU0', 'AL': 'AL0', 'ZN': 'ZN0', 'NI': 'NI0',
            'AU': 'AU0', 'AG': 'AG0', 'RB': 'RB0', 'HC': 'HC0',
            'M': 'M0', 'Y': 'Y0', 'P': 'P0', 'NR': 'NR0',
            'TA': 'TA0', 'EG': 'EG0', 'PP': 'PP0',
            'PB': 'PB0', 'J': 'J0', 'JM': 'JM0', 'I': 'I0',
            'SC': 'SC0', 'FU': 'FU0', 'BU': 'BU0', 'RU': 'RU0',
        }
        sym = symbol_map.get(symbol, f'{symbol}0')
        df = ak.futures_main_sina(symbol=sym)
        # AKShare 返回中文列名
        col_map = {
            '日期': 'date', '开盘价': 'open', '最高价': 'high',
            '最低价': 'low', '收盘价': 'close', '成交量': 'volume',
            '持仓量': 'position', '动态结算价': 's'
        }
        df = df.rename(columns=col_map)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df.columns = [c.lower() for c in df.columns]
        close_col = 'close' if 'close' in df.columns else df.columns[0]
        series = df[close_col].dropna()

        if start_date:
            series = series[series.index >= start_date]
        if end_date:
            series = series[series.index <= end_date]

        print(f'  [AKShare] {symbol} futures close: {len(series)} rows')
        return series

    except Exception as e:
        print(f'  [WARN] AKShare 获取 {symbol} 价格失败: {e}')
        return None


# ============ IC 计算核心 ============

def compute_ic_series(factor_series, forward_returns, method='pearson'):
    """
    计算滚动 IC 序列

    IC(t) = corr(factor(0:t), ret(t:t+n))

    参数：
        factor_series: 因子值序列
        forward_returns: 对应前瞻收益序列
        method: 'pearson' 或 'spearman'

    Returns: pd.Series (index=date, values=IC值)
    """
    # 对齐数据
    aligned = pd.DataFrame({
        'factor': factor_series,
        'fwd_ret': forward_returns
    }).dropna()

    if len(aligned) < MIN_PERIODS:
        return None

    if method == 'pearson':
        corr_func = pearsonr
    else:
        corr_func = spearmanr

    # 计算滚动 IC（使用 ROLLING_WINDOW）
    ic_list = []
    dates = aligned.index[ROLLING_WINDOW:]

    for i, date in enumerate(dates):
        window_data = aligned.iloc[max(0, i-ROLLING_WINDOW+1):i+1]
        if len(window_data) < MIN_PERIODS:
            continue

        factor_vals = window_data['factor'].values
        ret_vals = window_data['fwd_ret'].values

        # 去除 NaN
        mask = ~(np.isnan(factor_vals) | np.isnan(ret_vals))
        if mask.sum() < MIN_PERIODS:
            continue

        try:
            corr, pval = corr_func(factor_vals[mask], ret_vals[mask])
            if not np.isnan(corr):
                ic_list.append({'date': date, 'ic': corr, 'pval': pval})
        except:
            continue

    if not ic_list:
        return None

    ic_series = pd.DataFrame(ic_list).set_index('date')['ic']
    return ic_series


def compute_ic_metrics(ic_series):
    """
    计算 IC 统计指标
    """
    ic = ic_series.dropna()

    if len(ic) < MIN_PERIODS:
        return None

    metrics = {}

    # 基本统计
    metrics['ic_mean'] = ic.mean()
    metrics['ic_std'] = ic.std()
    metrics['ic_median'] = ic.median()
    metrics['ic_min'] = ic.min()
    metrics['ic_max'] = ic.max()
    metrics['ic_count'] = len(ic)

    # IR（信息比率）
    metrics['ir'] = metrics['ic_mean'] / metrics['ic_std'] if metrics['ic_std'] > 0 else 0

    # 正 IC 比例（胜率）
    metrics['win_rate'] = (ic > 0).mean()

    # t 统计量
    t_stat, p_val = ttest_1samp(ic.values, 0)
    metrics['t_stat'] = t_stat
    metrics['p_value'] = p_val
    metrics['significant'] = p_val < SIGNIFICANCE_LEVEL

    # 分位数
    metrics['ic_p25'] = ic.quantile(0.25)
    metrics['ic_p75'] = ic.quantile(0.75)
    metrics['ic_iqr'] = metrics['ic_p75'] - metrics['ic_p25']

    # 连续为正/负的最大天数
    sign_changes = ic.diff().fillna(0) != 0
    metrics['max_consecutive_pos'] = 0
    metrics['max_consecutive_neg'] = 0
    current_pos = current_neg = 0
    for s in ic > 0:
        if s:
            current_pos += 1
            current_neg = 0
            metrics['max_consecutive_pos'] = max(metrics['max_consecutive_pos'], current_pos)
        else:
            current_neg += 1
            current_pos = 0
            metrics['max_consecutive_neg'] = max(metrics['max_consecutive_neg'], current_neg)

    # IC 方向一致性
    metrics['ic_positive_pct'] = (ic > 0).mean() * 100
    metrics['direction'] = '正向' if metrics['ic_mean'] > 0 else '负向'

    # 评级
    metrics['rating'] = rate_ic(metrics['ic_mean'], metrics['ir'], metrics['t_stat'])

    return metrics


def rate_ic(ic_mean, ir, t_stat):
    """
    IC 评级
    """
    if ic_mean > IC_EXCELLENT and ir > IR_GOOD and abs(t_stat) > 3.0:
        return '🟢 优秀'
    elif ic_mean > IC_GOOD and ir > IR_MIN and abs(t_stat) > T_STAT_MIN:
        return '🟡 良好'
    elif ic_mean > IC_MIN and abs(t_stat) > T_STAT_MIN:
        return '🟠 及格'
    elif ic_mean > 0:
        return '🔴 偏弱'
    else:
        return '⚫ 无效'


def compute_decay_analysis(factor_series, price_series):
    """
    因子衰减分析：不同持有期的 IC 变化

    Returns: pd.DataFrame (持有期 -> IC均值)
    """
    decay_results = []

    for fd in FORWARD_DAYS:
        fwd_ret = compute_forward_return(price_series, fd)

        # 对齐
        aligned = pd.DataFrame({
            'factor': factor_series,
            'fwd_ret': fwd_ret
        }).dropna()

        if len(aligned) < MIN_PERIODS:
            continue

        ic_vals = []
        for i in range(ROLLING_WINDOW, len(aligned)):
            window = aligned.iloc[i-ROLLING_WINDOW:i]
            mask = ~(np.isnan(window['factor'].values) | np.isnan(window['fwd_ret'].values))
            if mask.sum() >= MIN_PERIODS:
                try:
                    c, _ = pearsonr(window['factor'].values[mask], window['fwd_ret'].values[mask])
                    if not np.isnan(c):
                        ic_vals.append(c)
                except:
                    continue

        if ic_vals:
            decay_results.append({
                'forward_days': fd,
                'ic_mean': np.mean(ic_vals),
                'ic_std': np.std(ic_vals),
                'ir': np.mean(ic_vals) / np.std(ic_vals) if np.std(ic_vals) > 0 else 0,
                'sample_count': len(ic_vals)
            })

    return pd.DataFrame(decay_results)


# ============ 因子相关性分析 ============

def compute_factor_correlation_matrix(factor_dict):
    """
    计算因子相关性矩阵
    """
    # 对齐所有因子
    df = pd.DataFrame(factor_dict)
    df = df.dropna()

    if df.shape[0] < MIN_PERIODS or df.shape[1] < 2:
        return None, None

    corr_matrix = df.corr(method='pearson')

    # 找出高相关对（|r| > 0.7）
    high_corr_pairs = []
    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i+1, len(cols)):
            r = corr_matrix.iloc[i, j]
            if abs(r) > 0.7:
                high_corr_pairs.append({
                    'factor1': cols[i],
                    'factor2': cols[j],
                    'correlation': round(r, 4),
                    'severity': '🔴 高危' if abs(r) > 0.9 else '🟡 警告'
                })

    return corr_matrix, high_corr_pairs


def schmidt_orthogonalize(factor_dict, target='price_ret'):
    """
    Schmidt 正交化：去除因子之间的线性相关性

    顺序：对每个因子，依次对前面已正交化因子回归，残差作为新因子值
    """
    df = pd.DataFrame(factor_dict)
    df = df.dropna()

    if df.shape[0] < MIN_PERIODS:
        return None

    orthogonalized = {}
    remaining = list(df.columns)

    # 第一个因子保持不变
    if remaining:
        first = remaining.pop(0)
        orthogonalized[first] = df[first].values

        # 对剩余因子依次正交化
        for factor in remaining:
            residuals = []
            x_cols = list(orthogonalized.keys())
            y_vals = df[factor].values

            for j in range(len(df)):
                # 回归
                X = np.column_stack([orthogonalized[c][j] for c in x_cols])
                y = y_vals[j]

                # 跳过 NaN
                if np.isnan(y):
                    residuals.append(np.nan)
                    continue

                if len(x_cols) == 1:
                    X_j = np.array([X[0]])
                else:
                    X_j = X.reshape(1, -1)

                if X_j.shape[1] > 0 and not np.any(np.isnan(X_j)):
                    try:
                        lr = LinearRegression()
                        lr.fit(X_j.reshape(-1, 1) if X_j.shape[1] == 1 else X_j,
                               np.array([y]))
                        residual = y - lr.predict(X_j.reshape(1, -1))[0]
                        residuals.append(residual)
                    except:
                        residuals.append(y)
                else:
                    residuals.append(y)

            orthogonalized[factor] = np.array(residuals)

    result = pd.DataFrame(orthogonalized, index=df.index)
    return result


# ============ 多重检验校正 ============

def bonferroni_correction(p_values, alpha=0.05):
    """
    Bonferroni 校正
    """
    n = len(p_values)
    adjusted = [min(p * n, 1.0) for p in p_values]
    return adjusted


def fdr_correction(p_values, q=0.05):
    """
    Benjamini-Hochberg FDR 校正
    """
    n = len(p_values)
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]

    adjusted = np.zeros(n)
    for i in range(n):
        adjusted[sorted_indices[i]] = sorted_p[i] * n / (i + 1)

    # 确保单调性
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)

    return adjusted.tolist()


# ============ 分层回测（Top-Bottom IC） ============

def compute_top_bottom_ic(factor_series, price_series, forward_n=5, n_groups=5):
    """
    分层测试：按因子值分组，看各组收益是否有显著差异

    IC_ls = mean(ret_top) - mean(ret_bottom)
    """
    fwd_ret = compute_forward_return(price_series, forward_n)

    aligned = pd.DataFrame({
        'factor': factor_series,
        'fwd_ret': fwd_ret
    }).dropna()

    if len(aligned) < MIN_PERIODS * 2:
        return None

    # 分组
    try:
        aligned['group'] = pd.qcut(aligned['factor'], q=n_groups, labels=False, duplicates='drop')
    except:
        return None

    group_returns = aligned.groupby('group')['fwd_ret'].mean()

    # IC_ls（Long-Short）
    if len(group_returns) >= 2:
        ic_ls = group_returns.iloc[-1] - group_returns.iloc[0]  # top - bottom
    else:
        ic_ls = 0

    # 多空收益率差
    results = {
        'ic_ls': ic_ls,
        'top_return': group_returns.iloc[-1] if len(group_returns) > 0 else 0,
        'bottom_return': group_returns.iloc[0] if len(group_returns) > 0 else 0,
        'group_count': len(group_returns),
        'spread_return': ic_ls,
        'groups': group_returns.to_dict()
    }

    return results


# ============ 动态 IC 加权 ============

def compute_ic_weighted_signal(factor_dict, price_series, alpha=0.3):
    """
    IC 加权信号合成

    weight_i(t) = α × IC_static + (1-α) × IC_recent(t)

    其中 IC_static = 全历史 IC 均值
          IC_recent(t) = 近期滚动 IC 均值

    综合信号 = Σ weight_i × zscore(factor_i)
    """
    forward_n = 5  # 默认 5 日前瞻
    fwd_ret = compute_forward_return(price_series, forward_n)

    weights = {}
    zscore_factors = {}

    for factor_code, factor_vals in factor_dict.items():
        ic_rolling = compute_ic_series(factor_vals, fwd_ret, method='pearson')

        if ic_rolling is None or len(ic_rolling) < MIN_PERIODS:
            continue

        # IC_static = 全历史均值
        ic_static = ic_rolling.mean()
        # IC_recent = 近 20 日均值
        ic_recent = ic_rolling.tail(20).mean()

        # 动态权重
        w = alpha * ic_static + (1 - alpha) * ic_recent
        weights[factor_code] = w

        # Z-score 标准化
        fs = factor_vals.dropna()
        z = (fs - fs.mean()) / (fs.std() + 1e-8)
        zscore_factors[factor_code] = z

    if not weights:
        return None, None

    # 归一化权重（保证符号一致）
    weight_sum = sum(abs(w) for w in weights.values())
    normalized_weights = {k: w / weight_sum for k, w in weights.items()}

    # 合成信号
    aligned = pd.DataFrame(zscore_factors)
    weights_s = pd.Series(normalized_weights)

    # 只保留两者都有的行
    common_idx = aligned.dropna().index

    signal = pd.Series(0.0, index=common_idx)
    for factor_code in aligned.columns:
        if factor_code in weights_s.index:
            signal += aligned[factor_code].loc[common_idx] * weights_s[factor_code]

    return signal, weights


# ============ 主报告生成 ============

def generate_report(symbol, results, forward_n=5):
    """
    生成结构化验证报告
    """
    report_lines = []
    report_lines.append(f"# 因子 IC 有效性验证报告")
    report_lines.append(f"**品种**: {symbol}")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**前瞻期**: {forward_n} 日")
    report_lines.append(f"**滚动窗口**: {ROLLING_WINDOW} 日")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # ---- 汇总表 ----
    report_lines.append("## 一、因子 IC 汇总（按 IC 均值降序）")

    if not results['ic_summary']:
        report_lines.append("*无可用数据*")
    else:
        rows = sorted(results['ic_summary'], key=lambda x: abs(x['ic_mean']), reverse=True)

        header = (
            "| 因子代码 | 因子名称 | IC均值 | IC标准差 | IR | t统计量 | p值 | "
            "胜率 | 评级 |\n"
            "|---|---|---:|---:|---:|---:|---:|---:|---|"
        )
        report_lines.append(header)

        for r in rows:
            sig_mark = '✓' if r['significant'] else '✗'
            report_lines.append(
                f"| {r['factor']} | {r['name']} | "
                f"{r['ic_mean']:+.4f} | {r['ic_std']:.4f} | "
                f"{r['ir']:.3f} | {r['t_stat']:.2f} | "
                f"{r['p_value']:.4f}{sig_mark} | "
                f"{r['win_rate']*100:.1f}% | {r['rating']} |"
            )

    report_lines.append("")
    report_lines.append("**评级标准**（SOUL.md 标准）：")
    report_lines.append(f"- 🟢 优秀：IC均值>{IC_EXCELLENT}，IR>{IR_GOOD}，|t|>{T_STAT_MIN}")
    report_lines.append(f"- 🟡 良好：IC均值>{IC_GOOD}，IR>{IR_MIN}，|t|>{T_STAT_MIN}")
    report_lines.append(f"- 🟠 及格：IC均值>{IC_MIN}，|t|>{T_STAT_MIN}")
    report_lines.append("")

    # ---- 衰减分析 ----
    if results['decay']:
        report_lines.append("## 二、因子衰减分析")
        report_lines.append("")
        report_lines.append("| 因子 | 1日IC | 5日IC | 10日IC | 20日IC | 最优持有期 |")
        report_lines.append("|---|---|---:|---:|---:|---:|---:|")

        for factor_code, decay_df in results['decay'].items():
            if decay_df is None or decay_df.empty:
                continue
            row = decay_df[decay_df['ic_mean'].abs() == decay_df['ic_mean'].abs().max()]
            if row.empty:
                continue
            best_holding = row.iloc[0]['forward_days']
            row_data = {fd: decay_df[decay_df['forward_days']==fd]['ic_mean'].values[0]
                       if fd in decay_df['forward_days'].values else np.nan
                       for fd in FORWARD_DAYS}
            row_str = f"| {factor_code} |"
            for fd in FORWARD_DAYS:
                val = row_data.get(fd, np.nan)
                row_str += f" {val:+.4f} |" if not np.isnan(val) else " — |"
            row_str += f" {best_holding:.0f}日 |"
            report_lines.append(row_str)
        report_lines.append("")

    # ---- 高相关因子对 ----
    if results['high_corr']:
        report_lines.append("## 三、因子相关性警告")
        report_lines.append("")
        report_lines.append("以下因子对相关性 > 0.7，存在信息重复，建议合并或剔除：")
        report_lines.append("")
        for pair in results['high_corr']:
            report_lines.append(
                f"- {pair['severity']} {pair['factor1']} ↔ {pair['factor2']} "
                f"(r={pair['correlation']:.4f})"
            )
        report_lines.append("")
    else:
        report_lines.append("## 三、因子相关性警告")
        report_lines.append("✅ 未发现高相关因子对（|r| > 0.7）")
        report_lines.append("")

    # ---- 多重检验校正 ----
    if results['multiple_test']:
        report_lines.append("## 四、多重检验校正")
        report_lines.append("")
        report_lines.append(f"检验 {results['multiple_test']['n_tests']} 个因子的显著性：")
        report_lines.append("")
        report_lines.append(f"- Bonferroni 校正后显著因子数：{results['multiple_test']['bonferroni_sig']}")
        report_lines.append(f"- FDR (q=0.05) 校正后显著因子数：{results['multiple_test']['fdr_sig']}")
        report_lines.append("")

    # ---- 动态 IC 加权 ----
    if results['ic_weights']:
        report_lines.append("## 五、IC 动态加权方案（α=0.3）")
        report_lines.append("")
        report_lines.append("| 因子代码 | IC静态权重 | 说明 |")
        report_lines.append("|---|---:|---|")
        for code, w in sorted(results['ic_weights'].items(),
                               key=lambda x: abs(x[1]), reverse=True):
            direction = '↑' if w > 0 else '↓'
            report_lines.append(f"| {code} | {w:+.4f}{direction} | "
                               f"{'做多信号' if w > 0 else '做空信号'} |")
        report_lines.append("")

    # ---- 结论 ----
    report_lines.append("## 六、因子有效性结论")

    valid_factors = [r for r in results['ic_summary']
                     if r['ic_mean'] > IC_MIN and r['significant']]
    weak_factors = [r for r in results['ic_summary']
                    if r['ic_mean'] > 0 and not r['significant']]
    invalid_factors = [r for r in results['ic_summary']
                       if r['ic_mean'] <= IC_MIN]

    report_lines.append("")
    if valid_factors:
        report_lines.append("✅ **有效因子（建议上线）**：")
        for r in valid_factors:
            report_lines.append(f"  - {r['factor']}（{r['name']}）IC={r['ic_mean']:.4f}, IR={r['ir']:.3f}")

    if weak_factors:
        report_lines.append("")
        report_lines.append("🟡 **偏弱因子（观察）**：")
        for r in weak_factors:
            report_lines.append(f"  - {r['factor']}（{r['name']}）IC={r['ic_mean']:.4f}, "
                               f"IR={r['ir']:.3f}（显著性问题）")

    if invalid_factors:
        report_lines.append("")
        report_lines.append("🔴 **建议剔除因子**：")
        for r in invalid_factors:
            report_lines.append(f"  - {r['factor']}（{r['name']}）IC={r['ic_mean']:.4f} < {IC_MIN}")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append(f"*本报告由因子分析师 IC 验证框架自动生成 | {datetime.now().strftime('%Y-%m-%d')}*")

    return '\n'.join(report_lines)


# ============ 主验证流程 ============

def validate_factors(symbol, factor_codes=None, start_date='2020-01-01',
                     end_date=None, forward_n=5):
    """
    主验证流程
    """
    print(f"\n{'='*60}")
    print(f"因子 IC 有效性验证 | 品种: {symbol} | 前瞻期: {forward_n}日")
    print(f"{'='*60}")

    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    results = {
        'ic_summary': [],
        'decay': {},
        'high_corr': [],
        'multiple_test': None,
        'ic_weights': {}
    }

    # ---- 步骤1：加载因子数据 ----
    print("\n[步骤1] 加载因子数据...")
    factor_data = {}
    for fc in factor_codes:
        series = load_factor_data(fc, start_date, end_date)
        if series is not None and len(series) > 0:
            factor_data[fc] = series
            print(f"  ✅ {fc}: {len(series)} 条数据 ({series.index[0].date()} ~ {series.index[-1].date()})")
        else:
            print(f"  ⏭️  {fc}: 无数据（待采集）")

    if len(factor_data) < 1:
        print("[WARN] 没有可用的因子数据，跳过 IC 计算")
        return results

    # ---- 步骤2：获取价格序列（前瞻收益计算） ----
    print("\n[步骤2] 获取价格序列（用于计算前瞻收益）...")
    price_series = None

    if symbol != 'SHARED':
        price_series = get_price_series(symbol, start_date, end_date)
        if price_series is not None and len(price_series) > 0:
            print(f'  ✅ {symbol}期货: {len(price_series)} 条数据')
        else:
            print(f'  [WARN] 无法获取 {symbol} 期货价格')
            print('  [INFO] 使用因子自身价格替代（验证因子与自身前瞻收益的IC）')
            # 用第一个因子替代
            first_factor = list(factor_data.values())[0]
            price_series = first_factor
    else:
        # 共用因子：用 USD/CNY 或 WTI 作为大类商品代理
        if 'USD_CNY_SPOT' in factor_data:
            price_series = factor_data['USD_CNY_SPOT']
            print('  ✅ 使用 USD/CNY 作为大类商品代理价格')

    if price_series is None or len(price_series) < MIN_PERIODS:
        print('[WARN] 价格数据不足，跳过 IC 计算')
        return results

    # ---- 步骤3：计算 IC ----
    print('\n[Step3] Computing IC (rolling_window=' + str(ROLLING_WINDOW) + 'd, forward=' + str(forward_n) + 'd)...')

    ic_raw_data = {}  # 原始 IC 序列

    for fc, factor_vals in factor_data.items():
        fwd_ret = compute_forward_return(price_series, forward_n)
        ic_series = compute_ic_series(factor_vals, fwd_ret, method='pearson')

        if ic_series is not None and len(ic_series) > 0:
            ic_raw_data[fc] = ic_series
            metrics = compute_ic_metrics(ic_series)

            if metrics:
                fdef = FACTOR_REGISTRY.get(fc, {})
                result = {
                    'factor': fc,
                    'name': fdef.get('name', fc),
                    'direction': fdef.get('direction', 1),
                    **metrics
                }
                results['ic_summary'].append(result)
                r = result['rating'].encode('utf-8').decode('utf-8')
                print('  ' + result['rating'] + ' ' + fc + ': IC=' + f"{metrics['ic_mean']:+.4f}" +
                      ', IR=' + f"{metrics['ir']:.3f}" + ', t=' + f"{metrics['t_stat']:.2f}" +
                      ', win_rate=' + f"{metrics['win_rate']*100:.1f}%")
        else:
            print('  [skip] ' + fc + ': insufficient data for IC calculation')

    # ---- 步骤4：衰减分析 ----
    if ic_raw_data:
        print('\n[Step4] Factor Decay Analysis...')
        first_factor = list(factor_data.keys())[0]
        for fc in list(ic_raw_data.keys())[:5]:  # max 5
            decay_df = compute_decay_analysis(
                factor_data[fc], price_series
            )
            if decay_df is not None and not decay_df.empty:
                results['decay'][fc] = decay_df
                print('  ' + fc + ': ' + decay_df[['forward_days', 'ic_mean']].to_string(index=False))

    # ---- 步骤5：相关性矩阵 ----
    if len(ic_raw_data) >= 2:
        print('\n[Step5] Factor Correlation Analysis...')
        corr_matrix, high_corr = compute_factor_correlation_matrix(factor_data)
        results['high_corr'] = high_corr or []
        if high_corr:
            for pair in high_corr:
                print('  ' + pair['severity'] + ' ' + pair['factor1'] + ' <-> ' +
                      pair['factor2'] + ': r=' + f"{pair['correlation']:.4f}")
        else:
            print('  [OK] No highly correlated factor pairs found')

    # ---- 步骤6：多重检验校正 ----
    if len(results['ic_summary']) >= 2:
        print('\n[Step6] Multiple Testing Correction...')
        p_values = [r['p_value'] for r in results['ic_summary']]
        bonferroni = bonferroni_correction(p_values, alpha=SIGNIFICANCE_LEVEL)
        fdr = fdr_correction(p_values, q=0.05)

        bonf_sig = sum(1 for p in bonferroni if p < SIGNIFICANCE_LEVEL)
        fdr_sig = sum(1 for p in fdr if p < SIGNIFICANCE_LEVEL)

        results['multiple_test'] = {
            'n_tests': len(p_values),
            'bonferroni_sig': bonf_sig,
            'fdr_sig': fdr_sig
        }
        print('  Bonferroni significant: ' + str(bonf_sig) + '/' + str(len(p_values)))
        print('  FDR (q=0.05) significant: ' + str(fdr_sig) + '/' + str(len(p_values)))

    # ---- 步骤7：IC 加权信号 ----
    if len(factor_data) >= 2:
        print('\n[Step7] IC-Weighted Signal Synthesis...')
        signal, weights = compute_ic_weighted_signal(factor_data, price_series, alpha=0.3)
        if weights:
            results['ic_weights'] = weights
            for code, w in sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True):
                print(f'  {code}: {w:+.4f}')

    # ---- 步骤8：生成报告 ----
    report = generate_report(symbol, results, forward_n)

    today_str = datetime.now().strftime('%Y%m%d')
    report_file = REPORT_PATH / f'IC_validation_{symbol}_{today_str}.md'
    with open(report_file, 'w', encoding='utf-8-sig') as f:
        f.write(report)

    print('\nReport generated: ' + str(report_file))

    # ---- 步骤9：JSON 输出（供后续使用） ----
    json_file = REPORT_PATH / f'IC_validation_{symbol}_{today_str}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, default=str, ensure_ascii=False, indent=2)
    print('JSON data saved: ' + str(json_file))

    return results


# ============ 命令行接口 ============

def main():
    parser = argparse.ArgumentParser(
        description='因子 IC 有效性验证框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  python validate_factor_ic.py --symbol CU --factors all --start 2020-01-01
  python validate_factor_ic.py --symbol SHARED --factors shared --start 2020-01-01
  python validate_factor_ic.py --symbol CU --factors CU_LME_3M_SPREAD,CU_LME_3M_CLOSE --start 2020-01-01
  python validate_factor_ic.py --symbol all --factors phase1 --start 2020-01-01 --forward 5
'''
    )
    parser.add_argument('--symbol', default='SHARED',
                       help='symbol code (e.g. CU/NR/AU) or SHARED for common factors')
    parser.add_argument('--factors', default='all',
                       help='factor codes, comma-separated; or all/phase1/phase4/shared')
    parser.add_argument('--start', default='2020-01-01',
                       help='start date (YYYY-MM-DD)')
    parser.add_argument('--end', default=None,
                       help='end date (YYYY-MM-DD)')
    parser.add_argument('--forward', type=int, default=5,
                       help='forward return period in days (default: 5)')

    args = parser.parse_args()

    # resolve factor list
    factor_map = {
        'all': list(FACTOR_REGISTRY.keys()),
        'phase1': [k for k, v in FACTOR_REGISTRY.items() if 'Phase 1' in v.get('comment', '')],
        'phase4': [k for k, v in FACTOR_REGISTRY.items() if 'Phase 4' in v.get('comment', '')],
        'shared': ['USD_CNY_SPOT', 'WTI_SPOT'],
    }

    if args.factors in factor_map:
        factor_codes = factor_map[args.factors]
    elif args.factors == 'all':
        if args.symbol == 'SHARED':
            factor_codes = ['USD_CNY_SPOT', 'WTI_SPOT']
        else:
            factor_codes = [k for k, v in FACTOR_REGISTRY.items()
                           if v.get('symbol') == args.symbol or v.get('symbol') == 'ALL']
    else:
        factor_codes = [f.strip() for f in args.factors.split(',')]

    print(f'\nFactors to validate ({len(factor_codes)}):')
    for fc in factor_codes:
        fdef = FACTOR_REGISTRY.get(fc, {})
        fname = fdef.get('name', '?')
        print(f'  - {fc}: {fname}')

    validate_factors(
        symbol=args.symbol,
        factor_codes=factor_codes,
        start_date=args.start,
        end_date=args.end,
        forward_n=args.forward
    )


if __name__ == '__main__':
    main()