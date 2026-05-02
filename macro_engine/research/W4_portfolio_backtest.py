#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W4 组合回测 - 等权合成 + 5日持有期
日期: 2026-04-23
"""

import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import pearsonr, spearmanr, ttest_1samp

warnings.filterwarnings('ignore')

# ============ Windows UTF-8 ============
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============ 路径配置 ============
DATA_BASE = Path(r'D:\futures_v6\macro_engine\data\crawlers')
REPORT_BASE = Path(r'D:\futures_v6\macro_engine\research\reports')
OUT_DIR = REPORT_BASE / 'W4_backtest'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============ 全局参数 ============
START_DATE = '2020-01-01'
END_DATE = '2025-12-31'
HOLDING = 5  # 持有期
ROLLING_IC_WINDOW = 60
MIN_PERIODS = 30
SIGNIFICANCE_LEVEL = 0.05
TX_COST = 0.0003  # 0.03% per trade

# 信号阈值：组合合成信号的 |z_score| >= 此值才生成交易信号
# 用于过滤低置信信号，降低无效换手（W4 回测中日均换手率 47%）
# 可在 settings.yaml 的 scoring.signal_zscore_threshold 中覆盖
ZSCORE_THRESHOLD = 0.5

# 尝试从 settings.yaml 覆盖
_settings_path = Path(r'D:\futures_v6\macro_engine\config\settings.yaml')
if _settings_path.exists():
    try:
        with open(_settings_path, 'r', encoding='utf-8') as _f:
            _cfg = yaml.safe_load(_f)
        _override = _cfg.get('scoring', {}).get('signal_zscore_threshold')
        if _override is not None and isinstance(_override, (int, float)):
            ZSCORE_THRESHOLD = float(_override)
            print(f'[CONFIG] zscore_threshold 从 settings.yaml 加载: {ZSCORE_THRESHOLD}')
    except Exception as e:
        print(f'[WARN] settings.yaml 读取失败，使用默认值: {e}')

# ============ 数据加载 ============

def load_csv(filepath, parse_dates=['date']):
    full = DATA_BASE / filepath
    if not full.exists():
        print(f'  [ERROR] 文件不存在: {full}')
        return None
    df = pd.read_csv(full, parse_dates=parse_dates)
    df = df.set_index('date').sort_index()
    return df


def compute_factor_series(fdef, start, end):
    df = load_csv(fdef['source_file'])
    if df is None:
        return None
    col = fdef['source_col']
    if col not in df.columns:
        print(f'  [ERROR] 列 {col} 不在文件中')
        return None
    series = df[col].dropna()
    series = series[(series.index >= start) & (series.index <= end)]
    if fdef['factor_type'] == 'price_diff':
        factor = series.diff()
    else:
        factor = series
    factor = factor.dropna()
    return factor


def get_target_price(fdef, start, end):
    df = load_csv(fdef['target_file'])
    if df is None:
        return None
    col = fdef['target_col']
    if col not in df.columns:
        col = df.columns[0]
    series = df[col].dropna()
    series = series[(series.index >= start) & (series.index <= end)]
    return series


def compute_forward_returns(price_series, forward_n):
    """前瞻N日收益率: ret(t) = price(t+n) / price(t) - 1"""
    fwd = price_series.pct_change(forward_n).shift(-forward_n)
    return fwd


# ============ 因子定义 ============
FACTORS = {
    'CU_SpreadDiff': {
        'name': 'LME铜SpreadDiff',
        'source_file': 'CU/daily/LME_copper_cash_3m_spread.csv',
        'source_col': 'close',
        'target_file': 'CU/daily/CU_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',
        'direction': 1,   # spread↑ → CU↑（正向）
    },
    'NI_SpreadDiff': {
        'name': 'LME镍SpreadDiff',
        'source_file': 'NI/daily/LME_nickel_cash_3m_spread.csv',
        'source_col': 'close',
        'target_file': 'NI/daily/NI_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',
        'direction': 1,   # spread↑ → NI↑（正向）
    },
    'AU_AG_ratio_diff': {
        'name': '金银比变化量',
        'source_file': '_shared/daily/AU_AG_ratio_corrected.csv',
        'source_col': 'au_ag_ratio_corrected',
        'target_file': 'AG/daily/AG_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',  # diff = ratio日变化量
        'direction': -1,  # ratio↑ → AG↓（金银比↑=白银相对走弱）
    },
}

# IC signs from single-factor backtest (5-day holding)
IC_SIGN = {
    'CU_SpreadDiff': +1,   # IC positive
    'NI_SpreadDiff': +1,   # IC positive
    'AU_AG_ratio_diff': -1, # IC negative
}


# ============ 核心回测函数 ============

def zscore(series):
    mu = series.mean()
    sigma = series.std()
    if sigma == 0:
        return pd.Series(0, index=series.index)
    return (series - mu) / sigma


def build_portfolio():
    """
    主回测流程：
    1. 加载各因子数据
    2. 计算每日组合信号（等权合成，IC sign加权，normalize）
    3. 计算组合收益
    4. 输出评估指标和图表
    """
    print('=' * 70)
    print('W4 组合回测 | 等权合成 | 5日持有 | 多空组合')
    print('=' * 70)

    # ---------- 1. 加载所有因子和价格 ----------
    factor_data = {}
    for fname, fdef in FACTORS.items():
        print(f'\n加载因子: {fname}')
        factor = compute_factor_series(fdef, START_DATE, END_DATE)
        price = get_target_price(fdef, START_DATE, END_DATE)
        if factor is None or price is None:
            print(f'  [SKIP] {fname}: 数据不足')
            continue
        print(f'  因子: {len(factor)} 条 | 价格: {len(price)} 条')
        factor_data[fname] = {
            'factor': factor,
            'price': price,
            'direction': fdef['direction'],
        }

    # ---------- 2. 对齐所有数据到共同交易日 ----------
    all_dates = None
    for fname, fd in factor_data.items():
        dates = fd['factor'].index.union(fd['price'].index)
        if all_dates is None:
            all_dates = dates
        else:
            all_dates = all_dates.union(dates)
    all_dates = all_dates.sort_values()
    print(f'\n共同交易日范围: {all_dates[0].date()} ~ {all_dates[-1].date()} ({len(all_dates)} 天)')

    # ---------- 3. 计算各因子前瞻收益 ----------
    for fname, fd in factor_data.items():
        fwd_ret = compute_forward_returns(fd['price'], HOLDING)
        fd['fwd_ret'] = fwd_ret

    # ---------- 4. 计算每日 IC sign * zscore 组合信号 ----------
    # 每日: signal_raw = sign(IC_1)*z_1 + sign(IC_2)*z_2 + sign(IC_3)*z_3
    #       signal = signal_raw / |signal_raw|  (方向: +1=Long, -1=Short, 0=neutral)
    
    # 对齐所有因子到共同日期
    aligned_factors = {}
    for fname, fd in factor_data.items():
        f_aligned = fd['factor'].reindex(all_dates)
        r_aligned = fd['fwd_ret'].reindex(all_dates)
        aligned_factors[fname] = {'factor': f_aligned, 'fwd_ret': r_aligned}

    # 计算 zscore
    zscore_dict = {}
    for fname, fd in aligned_factors.items():
        z = zscore(fd['factor'].dropna())
        zscore_dict[fname] = z

    # 计算组合信号
    signal_raw_series = []
    for date in all_dates:
        total = 0
        for fname in FACTORS.keys():
            z_val = zscore_dict[fname].get(date, np.nan)
            if not np.isnan(z_val):
                total += IC_SIGN[fname] * z_val
        signal_raw_series.append({'date': date, 'signal_raw': total})

    signal_raw_df = pd.DataFrame(signal_raw_series).set_index('date')['signal_raw']
    signal_raw_df.name = 'signal_raw'

    # --- z-score 阈值过滤 ---
    # 仅当 |signal_raw| >= ZSCORE_THRESHOLD 时生成离散信号
    # 否则 signal = 0（不下单），保持向后兼容
    def _apply_threshold(x):
        if abs(x) >= ZSCORE_THRESHOLD:
            return np.sign(x)
        return 0

    signal = signal_raw_df.apply(_apply_threshold)
    signal.name = 'signal'

    # 对齐前瞻收益
    # 组合前瞻收益 = (signal_t * fwd_ret_t_CU + signal_t * fwd_ret_t_NI + signal_t * fwd_ret_t_AG) / 3
    # 注意: signal 方向已包含 IC sign，所以直接 signal * fwd_ret
    port_fwd_rets = []
    for date in all_dates:
        day_rets = []
        for fname, fd in aligned_factors.items():
            sig = signal.get(date, 0)
            fwd = fd['fwd_ret'].get(date, np.nan)
            if not np.isnan(fwd) and sig != 0:
                day_rets.append(sig * fwd)
        if day_rets:
            port_fwd_rets.append({'date': date, 'port_ret': np.mean(day_rets)})
        else:
            port_fwd_rets.append({'date': date, 'port_ret': np.nan})

    port_df = pd.DataFrame(port_fwd_rets).set_index('date')['port_ret']
    port_df.name = 'portfolio_return'

    # ---------- 5. 计算 IC（组合信号 vs 各品种前瞻收益）----------
    ic_cu = compute_ic_single(signal, aligned_factors['CU_SpreadDiff']['fwd_ret'])
    ic_ni = compute_ic_single(signal, aligned_factors['NI_SpreadDiff']['fwd_ret'])
    ic_ag = compute_ic_single(signal, aligned_factors['AU_AG_ratio_diff']['fwd_ret'])

    # ---------- 6. 累计收益计算 ----------
    ret = port_df.dropna()
    equity = (1 + ret).cumprod()
    equity.name = 'equity'

    # 换手率计算
    prev_signal = signal.shift(1)
    turnover = (signal != prev_signal).astype(float)
    avg_turnover = turnover.mean()
    num_trades = int(turnover.sum())

    # ---------- 7. 评估指标 ----------
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1 if equity.iloc[0] != 0 else 0
    n_periods = max(len(ret), 1)
    annual_ret = (1 + total_ret) ** (252 / n_periods) - 1
    daily_vol = ret.std()
    annual_vol = daily_vol * np.sqrt(252)
    sharpe = annual_ret / annual_vol if annual_vol > 0 else 0

    # 最大回撤
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_dd = drawdown.min()
    calmar = annual_ret / abs(max_dd) if max_dd != 0 else 0

    # 胜率
    win_rate = (ret > 0).mean()
    
    # 盈亏比
    gains = ret[ret > 0]
    losses = ret[ret < 0]
    avg_gain = gains.mean() if len(gains) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 1e-10
    profit_loss_ratio = avg_gain / avg_loss

    # 考虑交易成本后的 Sharpe
    # 每次换手损失 0.03% * 2（买入+卖出）
    annual_turnover_cost = avg_turnover * 2 * TX_COST * 252
    net_annual_ret = annual_ret - annual_turnover_cost
    net_sharpe = net_annual_ret / annual_vol if annual_vol > 0 else 0

    print(f'\n========== 组合回测结果 ==========')
    print(f'年化收益:      {annual_ret*100:.2f}%')
    print(f'Total Return:  {total_ret*100:.2f}%')
    print(f'Sharpe:       {sharpe:.3f}')
    print(f'Net Sharpe:   {net_sharpe:.3f} (after {annual_turnover_cost*100:.2f}% annual TC)')
    print(f'Max Drawdown: {max_dd*100:.2f}%')
    print(f'Calmar:       {calmar:.3f}')
    print(f'Win Rate:     {win_rate*100:.2f}%')
    print(f'Profit/Loss:  {profit_loss_ratio:.3f}')
    print(f'Turnover:     {avg_turnover*100:.2f}%/day ({num_trades} trades)')
    print(f'IC vs CU:     {ic_cu["ic_mean"]:+.4f} (IR={ic_cu["ir"]:.3f})')
    print(f'IC vs NI:     {ic_ni["ic_mean"]:+.4f} (IR={ic_ni["ir"]:.3f})')
    print(f'IC vs AG:     {ic_ag["ic_mean"]:+.4f} (IR={ic_ag["ir"]:.3f})')

    # ---------- 8. 生成图表 ----------
    plot_equity_and_drawdown(equity, drawdown, OUT_DIR / 'portfolio_equity.png', OUT_DIR / 'portfolio_drawdown.png')
    plot_signal_turnover(signal, turnover, OUT_DIR / 'portfolio_signal.png')

    # ---------- 9. 保存 JSON ----------
    import json
    json_data = {
        'portfolio_name': 'W4_Portfolio_EqualWeight',
        'backtest_date': '2026-04-23',
        'period': f'{START_DATE} ~ {END_DATE}',
        'holding_period': HOLDING,
        'factors': list(FACTORS.keys()),
        'weight_scheme': 'equal_weight_with_IC_sign',
        'metrics': {
            'total_return': float(total_ret),
            'annual_return': float(annual_ret),
            'sharpe': float(sharpe),
            'net_sharpe_after_tc': float(net_sharpe),
            'annual_turnover_cost': float(annual_turnover_cost),
            'max_drawdown': float(max_dd),
            'calmar': float(calmar),
            'win_rate': float(win_rate),
            'profit_loss_ratio': float(profit_loss_ratio),
            'avg_daily_turnover': float(avg_turnover),
            'num_trades': int(num_trades),
            'annual_vol': float(annual_vol),
            'ic_vs_cu': {'ic_mean': float(ic_cu['ic_mean']), 'ir': float(ic_cu['ir']), 't_stat': float(ic_cu['t_stat'])},
            'ic_vs_ni': {'ic_mean': float(ic_ni['ic_mean']), 'ir': float(ic_ni['ir']), 't_stat': float(ic_ni['t_stat'])},
            'ic_vs_ag': {'ic_mean': float(ic_ag['ic_mean']), 'ir': float(ic_ag['ir']), 't_stat': float(ic_ag['t_stat'])},
        },
        'equity_series': {str(k.date()): float(v) for k, v in zip(equity.index, equity.values) if not np.isnan(v)},
        'drawdown_series': {str(k.date()): float(v) for k, v in zip(drawdown.index, drawdown.values) if not np.isnan(v)},
    }
    json_file = OUT_DIR / 'W4_portfolio_backtest_20260423.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f'\n  [JSON] {json_file}')

    return json_data, equity, drawdown, signal


def compute_ic_single(signal_series, fwd_ret_series):
    """计算组合信号与单个品种前瞻收益的 IC"""
    aligned = pd.DataFrame({'signal': signal_series, 'fwd_ret': fwd_ret_series}).dropna()
    if len(aligned) < MIN_PERIODS:
        return {'ic_mean': 0, 'ir': 0, 't_stat': 0, 'win_rate': 0}
    ic_vals = []
    for i in range(ROLLING_IC_WINDOW, len(aligned)):
        w = aligned.iloc[i-ROLLING_IC_WINDOW:i]
        mask = ~(np.isnan(w['signal'].values) | np.isnan(w['fwd_ret'].values))
        if mask.sum() < MIN_PERIODS:
            continue
        try:
            c, _ = pearsonr(w['signal'].values[mask], w['fwd_ret'].values[mask])
            if not np.isnan(c):
                ic_vals.append(c)
        except:
            continue
    if not ic_vals:
        return {'ic_mean': 0, 'ir': 0, 't_stat': 0, 'win_rate': 0}
    ic_series = pd.Series(ic_vals)
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    ir = ic_mean / ic_std if ic_std > 0 else 0
    t_stat, p_val = ttest_1samp(ic_series.values, 0)
    win_rate = (ic_series > 0).mean()
    return {
        'ic_mean': ic_mean,
        'ic_std': ic_std,
        'ir': ir,
        't_stat': t_stat,
        'p_value': p_val,
        'win_rate': win_rate,
        'ic_count': len(ic_series),
    }


def plot_equity_and_drawdown(equity, drawdown, eq_path, dd_path):
    """Equity curve + drawdown"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), dpi=120)

    # Equity
    eq_norm = equity / equity.iloc[0]
    ax1.plot(eq_norm.index, eq_norm.values, color='#2196F3', linewidth=1.5, label='Portfolio')
    ax1.set_title('W4 Portfolio Equity Curve (Long-Short, 5-Day Holding)', fontsize=13)
    ax1.set_ylabel('Cumulative Return (x)')
    ax1.axhline(1.0, color='black', linewidth=0.8, linestyle='--')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # Drawdown
    ax2.fill_between(drawdown.index, drawdown.values * 100, 0,
                     color='#FF5722', alpha=0.4, label='Drawdown')
    ax2.plot(drawdown.index, drawdown.values * 100, color='#FF5722', linewidth=0.8)
    ax2.set_title('Portfolio Drawdown (%)', fontsize=13)
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

    plt.savefig(eq_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  [Chart] Equity saved: {eq_path}')

    # Drawdown only
    fig2, ax2 = plt.subplots(figsize=(14, 4), dpi=120)
    ax2.fill_between(drawdown.index, drawdown.values * 100, 0,
                     color='#FF5722', alpha=0.4, label='Drawdown')
    ax2.plot(drawdown.index, drawdown.values * 100, color='#FF5722', linewidth=0.8)
    ax2.set_title('W4 Portfolio Drawdown (%)', fontsize=13)
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.savefig(dd_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  [Chart] Drawdown saved: {dd_path}')


def plot_signal_turnover(signal, turnover, out_path):
    """Signal distribution + turnover"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), dpi=120)
    
    # Signal histogram
    sig_vals = signal[signal != 0].dropna()
    colors = ['#4CAF50' if v > 0 else '#F44336' for v in sig_vals]
    ax1.hist(sig_vals, bins=50, color='#2196F3', alpha=0.7)
    ax1.set_title('Portfolio Signal Distribution (Non-zero)', fontsize=13)
    ax1.set_xlabel('Signal (+1=Long, -1=Short)')
    ax1.grid(True, alpha=0.3)
    
    # Turnover time series (30d rolling avg)
    turnover_ma = turnover.rolling(30).mean() * 100
    turnover_ma.plot(ax=ax2, color='#FF9800', linewidth=1.2, label='30d MA')
    turnover.plot(ax=ax2, color='#FF9800', alpha=0.3, linewidth=0.5)
    ax2.set_title('Daily Portfolio Turnover (%)', fontsize=13)
    ax2.set_ylabel('Turnover (%)')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  [Chart] Signal+Turnover saved: {out_path}')


if __name__ == '__main__':
    json_data, equity, drawdown, signal = build_portfolio()
