#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W4 回测 - 单因子回测验证（04-22）
4 个入池因子：
  1. LME Cu SpreadDiff（CU）  → LME铜3M价格日变化量
  2. LME Ni SpreadDiff（NI）  → LME镍3M价格日变化量
  3. 金银比 SGE/1000（AG）     → AU/AG ratio 日度变化量
  4. USD/CNY diff（已剔除）
  → 实际回测3个

回测参数：
  - 周期：2020-01-01 ~ 2025-12-31
  - 允许做空
  - 持有期：统一（5日）
  - 频率：日频
"""

import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
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
ROLLING_IC_WINDOW = 60    # 滚动IC窗口
HOLDING_PERIODS = [1, 5, 10, 20]  # 持有期（天）
MIN_PERIODS = 30
SIGNIFICANCE_LEVEL = 0.05

# ============ 因子定义 ============
# SpreadDiff = day-over-day change in LME 3M close price
# 金银比因子 = au_ag_ratio 的日度变化（不是比值本身）
FACTORS = {
    'CU_SpreadDiff': {
        'name': 'LME铜SpreadDiff（CU）',
        'source_file': 'CU/daily/LME_copper_cash_3m_spread.csv',
        'source_col': 'close',       # LME 3M close
        'target_file': 'CU/daily/CU_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',  # diff of source_col
        'direction': 1,              # spread↑ → CU↑（正向）
        'symbol': 'CU',
    },
    'NI_SpreadDiff': {
        'name': 'LME镍SpreadDiff（NI）',
        'source_file': 'NI/daily/LME_nickel_cash_3m_spread.csv',
        'source_col': 'close',       # LME 3M close
        'target_file': 'NI/daily/NI_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',
        'direction': 1,              # spread↑ → NI↑（正向）
        'symbol': 'NI',
    },
    'AU_AG_ratio_diff': {
        'name': '金银比变化量（AG）',
        'source_file': '_shared/daily/AU_AG_ratio_corrected.csv',
        'source_col': 'au_ag_ratio_corrected',
        'target_file': 'AG/daily/AG_fut_close.csv',
        'target_col': 'close',
        'factor_type': 'price_diff',  # diff of ratio → ratio变化量
        'direction': -1,             # ratio↑ → AG↓（金银比↑=白银相对走弱）
        'symbol': 'AG',
    },
}

# ============ 数据加载 ============

def load_csv(filepath, parse_dates=['date']):
    """加载CSV，返回以date为索引的DataFrame"""
    full = DATA_BASE / filepath
    if not full.exists():
        print(f'  [ERROR] 文件不存在: {full}')
        return None
    df = pd.read_csv(full, parse_dates=parse_dates)
    df = df.set_index('date').sort_index()
    return df


def compute_factor_series(fdef, start, end):
    """
    计算因子序列
    factor_type='price_diff': source_col.diff() 作为因子值
    """
    df = load_csv(fdef['source_file'])
    if df is None:
        return None

    col = fdef['source_col']
    if col not in df.columns:
        print(f'  [ERROR] 列 {col} 不在 {fdef["source_file"]} 中')
        return None

    series = df[col].dropna()
    series = series[(series.index >= start) & (series.index <= end)]

    # 计算因子值
    if fdef['factor_type'] == 'price_diff':
        # SpreadDiff = day-over-day change（日变化量）
        factor = series.diff()
    else:
        factor = series

    factor = factor.dropna()
    factor.name = list(FACTORS.keys())[list(FACTORS.values()).index(fdef)]
    return factor


def get_target_price(fdef, start, end):
    """获取期货价格序列（前瞻收益计算用）"""
    df = load_csv(fdef['target_file'])
    if df is None:
        return None
    col = fdef['target_col']
    if col not in df.columns:
        # 尝试第一列
        col = df.columns[0]
    series = df[col].dropna()
    series = series[(series.index >= start) & (series.index <= end)]
    return series


# ============ IC 计算 ============

def compute_forward_returns(price_series, forward_n):
    """
    前瞻N日收益率
    ret(t) = price(t+n) / price(t) - 1
    """
    fwd = price_series.pct_change(forward_n).shift(-forward_n)
    return fwd


def compute_rolling_ic(factor_series, fwd_returns, window=ROLLING_IC_WINDOW):
    """
    滚动 IC 序列（Pearson）
    """
    aligned = pd.DataFrame({
        'factor': factor_series,
        'fwd_ret': fwd_returns
    }).dropna()

    if len(aligned) < window:
        return None

    ic_list = []
    for i in range(window, len(aligned)):
        w = aligned.iloc[i-window:i]
        mask = ~(np.isnan(w['factor'].values) | np.isnan(w['fwd_ret'].values))
        if mask.sum() < MIN_PERIODS:
            continue
        try:
            c, _ = pearsonr(w['factor'].values[mask], w['fwd_ret'].values[mask])
            if not np.isnan(c):
                ic_list.append({'date': aligned.index[i], 'ic': c})
        except:
            continue

    if not ic_list:
        return None
    return pd.DataFrame(ic_list).set_index('date')['ic']


def compute_ic_metrics(ic_series):
    """计算 IC 统计指标"""
    ic = ic_series.dropna()
    if len(ic) < MIN_PERIODS:
        return None

    m = {}
    m['ic_mean'] = ic.mean()
    m['ic_std'] = ic.std()
    m['ir'] = m['ic_mean'] / m['ic_std'] if m['ic_std'] > 0 else 0
    m['win_rate'] = (ic > 0).mean()
    t_stat, p_val = ttest_1samp(ic.values, 0)
    m['t_stat'] = t_stat
    m['p_value'] = p_val
    m['significant'] = p_val < SIGNIFICANCE_LEVEL
    m['ic_count'] = len(ic)
    m['ic_min'] = ic.min()
    m['ic_max'] = ic.max()
    m['rating'] = rate_ic(m['ic_mean'], m['ir'], abs(m['t_stat']))
    return m


def rate_ic(ic_mean, ir, t_abs):
    """IC 评级"""
    if abs(ic_mean) > 0.08 and ir > 0.5 and t_abs > 3.0:
        return '🟢 优秀'
    elif abs(ic_mean) > 0.05 and ir > 0.3 and t_abs > 2.0:
        return '🟡 良好'
    elif abs(ic_mean) > 0.02 and t_abs > 2.0:
        return '🟠 及格'
    elif abs(ic_mean) > 0:
        return '🔴 偏弱'
    else:
        return '⚫ 无效'


# ============ 回测信号生成 ============

def generate_signal(factor_series, direction):
    """
    生成做多/做空信号
    direction=1: 因子值↑ → 偏多（Long）
    direction=-1: 因子值↑ → 偏空（Short）
    信号：因子值 > 0 → Long/Short 取决于 direction
    """
    # 因子值标准化（z-score）后再生成信号
    mu = factor_series.mean()
    sigma = factor_series.std()
    if sigma == 0:
        return pd.Series(0, index=factor_series.index)
    z = (factor_series - mu) / sigma

    # 信号：z > 0 → Long Signal; z < 0 → Short Signal
    # Long-Short 组合：signal = sign(z) * direction
    signal = np.sign(z) * direction
    return pd.Series(signal, index=factor_series.index)


def compute_factor_return(factor_series, fwd_returns, direction):
    """
    计算因子收益（多空组合）
    每日信号 × 前瞻收益
    """
    signal = generate_signal(factor_series, direction)
    aligned = pd.DataFrame({
        'signal': signal,
        'fwd_ret': fwd_returns
    }).dropna()

    # 因子收益 = 信号 × 前瞻收益（做空收益 = -signal × fwd_ret）
    aligned['factor_ret'] = aligned['signal'] * aligned['fwd_ret']
    return aligned['factor_ret']


def compute_cumulative_equity(factor_returns):
    """计算累计收益曲线"""
    # 去除NaN
    ret = factor_returns.dropna()
    # 等权每日收益
    equity = (1 + ret).cumprod()
    equity.name = 'equity'
    return equity


# ============ 图表绘制 ============

def plot_ic_series(ic_dict, output_path):
    """绘制 IC 序列对比图"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), dpi=100)

    colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0']

    # 上图：IC 序列
    ax1 = axes[0]
    for (fname, ic_s), color in zip(ic_dict.items(), colors):
        if ic_s is not None and len(ic_s) > 0:
            ic_s.plot(ax=ax1, label=fname, color=color, alpha=0.7, linewidth=1.0)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title('Rolling IC Series (60-day window)', fontsize=13)
    ax1.set_ylabel('IC')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # 下图：累计 IC（平均）
    ax2 = axes[1]
    for (fname, ic_s), color in zip(ic_dict.items(), colors):
        if ic_s is not None and len(ic_s) > 0:
            cum_ic = ic_s.cumsum()
            cum_ic.plot(ax=ax2, label=fname, color=color, alpha=0.7, linewidth=1.5)
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_title('Cumulative IC (Running Sum)', fontsize=13)
    ax2.set_ylabel('Cumulative IC')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  [Chart] IC series saved: {output_path}')


def plot_equity_curves(equity_dict, output_path):
    """绘制累计收益曲线（多因子）"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), dpi=100)

    colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0']

    # 上图：各因子 equity curve
    ax1 = axes[0]
    for (fname, eq), color in zip(equity_dict.items(), colors):
        if eq is not None and len(eq) > 0:
            # 归一化到 1.0
            eq_norm = eq / eq.iloc[0] if eq.iloc[0] != 0 else eq
            eq_norm.plot(ax=ax1, label=fname, color=color, alpha=0.8, linewidth=1.2)
    ax1.axhline(1.0, color='black', linewidth=0.8, linestyle='--')
    ax1.set_title('Single Factor Equity Curve (Long-Short, Normalized to 1.0)', fontsize=13)
    ax1.set_ylabel('Cumulative Return (x)')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # 下图：因子收益散点（按年度）
    ax2 = axes[1]
    for (fname, eq), color in zip(equity_dict.items(), colors):
        if eq is not None and len(eq) > 0:
            ret = eq.pct_change().dropna()
            yearly_ret = ret.groupby(ret.index.year).sum() * 100
            bars = ax2.bar(yearly_ret.index.astype(str), yearly_ret.values,
                           alpha=0.6, label=fname, color=color)
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_title('Annual Returns by Factor (%)', fontsize=13)
    ax2.set_ylabel('Return (%)')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'  [Chart] Equity curves saved: {output_path}')


def plot_ic_heatmap(ic_dict, output_path):
    """绘制不同持有期的 IC 热力图"""
    # ic_dict: {factor_name: {forward_n: ic_series}}
    pass  # 简化版：直接用柱状图


def compute_decay_summary(all_ic_results):
    """
    汇总不同持有期的 IC 指标
    all_ic_results: {factor_name: {forward_n: {'ic_series': ..., 'metrics': {...}}}}
    """
    decay_rows = []
    for fname, fn_dict in all_ic_results.items():
        row = {'因子': fname}
        for fn, res in fn_dict.items():
            m = res.get('metrics')
            if m:
                row[f'IC_{fn}d'] = m['ic_mean']
                row[f'IR_{fn}d'] = m['ir']
                row[f't_{fn}d'] = m['t_stat']
                row[f'WR_{fn}d'] = m['win_rate']
        decay_rows.append(row)
    return pd.DataFrame(decay_rows).set_index('因子')


# ============ 主回测流程 ============

def run_backtest():
    print('=' * 70)
    print('W4 单因子回测验证 | 2020-01-01 ~ 2025-12-31')
    print('=' * 70)

    results = {}
    all_ic_results = {}  # {fname: {forward_n: {'ic_series', 'metrics'}}}

    for fname, fdef in FACTORS.items():
        print(f'\n{"-"*60}')
        print(f'处理因子: {fname} ({fdef["name"]})')
        print(f'{"-"*60}')

        # 1. 加载因子数据
        factor = compute_factor_series(fdef, START_DATE, END_DATE)
        if factor is None or len(factor) < MIN_PERIODS:
            print(f'  [SKIP] {fname}: 数据不足')
            continue

        print(f'  因子序列: {len(factor)} 条 ({factor.index[0].date()} ~ {factor.index[-1].date()})')

        # 2. 加载期货价格（用于计算前瞻收益）
        price = get_target_price(fdef, START_DATE, END_DATE)
        if price is None or len(price) < MIN_PERIODS:
            print(f'  [SKIP] {fname}: 期货价格数据不足')
            continue

        print(f'  期货价格: {len(price)} 条 ({price.index[0].date()} ~ {price.index[-1].date()})')

        # 3. 多持有期 IC 分析
        fn_ic_series = {}
        fn_metrics = {}

        for fn in HOLDING_PERIODS:
            fwd_ret = compute_forward_returns(price, fn)
            ic_s = compute_rolling_ic(factor, fwd_ret, window=ROLLING_IC_WINDOW)

            if ic_s is not None and len(ic_s) > 0:
                metrics = compute_ic_metrics(ic_s)
                fn_ic_series[fn] = ic_s
                fn_metrics[fn] = metrics
                print(f'  [{fn}d] IC={metrics["ic_mean"]:+.4f} | IR={metrics["ir"]:.3f} | '
                      f't={metrics["t_stat"]:.2f} | 胜率={metrics["win_rate"]*100:.1f}% | '
                      f'{metrics["rating"]}')

        if not fn_ic_series:
            print(f'  [SKIP] {fname}: 所有持有期 IC 计算失败')
            continue

        # 4. 计算累计收益（使用最佳持有期，或统一5日）
        holding = 5  # 统一持有期
        fwd_ret = compute_forward_returns(price, holding)
        factor_ret = compute_factor_return(factor, fwd_ret, fdef['direction'])
        equity = compute_cumulative_equity(factor_ret)

        # 计算评估指标
        ret = factor_ret.dropna()
        total_ret = equity.iloc[-1] / equity.iloc[0] - 1 if equity.iloc[0] != 0 else 0
        annual_ret = (1 + total_ret) ** (252 / max(len(ret), 1)) - 1
        daily_ret_std = ret.std()
        annual_vol = daily_ret_std * np.sqrt(252)
        sharpe = annual_ret / annual_vol if annual_vol > 0 else 0

        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()

        # Calmar
        calmar = annual_ret / abs(max_dd) if max_dd != 0 else 0

        print(f'  [5日equity] 总收益={total_ret*100:.2f}% | 年化={annual_ret*100:.2f}% | '
              f'Sharpe={sharpe:.3f} | 最大回撤={max_dd*100:.2f}% | Calmar={calmar:.3f}')

        all_ic_results[fname] = {
            fn: {'ic_series': ic_s, 'metrics': m}
            for fn, (ic_s, m) in enumerate(zip(fn_ic_series.values(), fn_metrics.values()))
        }
        # 重建（保留完整结构）
        all_ic_results[fname] = {}
        for fn in HOLDING_PERIODS:
            all_ic_results[fname][fn] = {
                'ic_series': fn_ic_series.get(fn),
                'metrics': fn_metrics.get(fn)
            }

        results[fname] = {
            'factor': factor,
            'price': price,
            'equity': equity,
            'factor_ret': factor_ret,
            'total_ret': total_ret,
            'annual_ret': annual_ret,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'calmar': calmar,
            'ic_series': fn_ic_series,
            'metrics': fn_metrics,
            'direction': fdef['direction'],
        }

    # ============ 图表 ============
    print('\n' + '='*60)
    print('生成图表...')

    # IC 序列图
    ic_plot_dict = {
        fname: results[fname]['ic_series'].get(5)  # 5日 IC
        for fname in results
    }
    plot_ic_series(ic_plot_dict, OUT_DIR / 'single_factor_IC_series.png')

    # Equity 曲线图
    equity_plot_dict = {fname: results[fname]['equity'] for fname in results}
    plot_equity_curves(equity_plot_dict, OUT_DIR / 'single_factor_equity.png')

    # ============ 汇总报告 ============
    print('\n' + '='*60)
    print('生成报告...')

    report_lines = []
    report_lines.append('# W4 单因子回测验证报告')
    report_lines.append(f'**日期**: 2026-04-22')
    report_lines.append(f'**回测周期**: 2020-01-01 ~ 2025-12-31（6年）')
    report_lines.append(f'**持有期**: 统一 5 日')
    report_lines.append(f'**做空**: ✅ 允许（多空组合）')
    report_lines.append('')
    report_lines.append('---')
    report_lines.append('')

    # ---- 表1: 因子 IC 汇总（各持有期）----
    report_lines.append('## 一、多持有期 IC 汇总')
    report_lines.append('')

    rows = []
    for fname, res in results.items():
        row = {'因子': fname}
        metrics_map = res['metrics']
        # 找最优持有期
        best_fn = None
        best_ic = -999
        for fn in HOLDING_PERIODS:
            m = metrics_map.get(fn)
            if m and abs(m['ic_mean']) > best_ic:
                best_ic = abs(m['ic_mean'])
                best_fn = fn

        for fn in HOLDING_PERIODS:
            m = metrics_map.get(fn)
            if m:
                row[f'IC_{fn}d'] = f"{m['ic_mean']:+.4f}"
                row[f'IR_{fn}d'] = f"{m['ir']:.3f}"
                row[f'WR_{fn}d'] = f"{m['win_rate']*100:.1f}%"
                row[f't_{fn}d'] = f"{m['t_stat']:.2f}"
                row[f'评级_{fn}d'] = m['rating']
            else:
                row[f'IC_{fn}d'] = '—'
                row[f'IR_{fn}d'] = '—'
                row[f'WR_{fn}d'] = '—'
                row[f't_{fn}d'] = '—'
                row[f'评级_{fn}d'] = '—'

        row['最优持有期'] = f'{best_fn}d' if best_fn else '—'
        rows.append(row)

    # 打印表格
    cols = ['因子'] + [c for c in rows[0].keys() if c != '因子']
    header = '| ' + ' | '.join(cols) + ' |'
    sep = '|' + '|'.join(['---'] * len(cols)) + '|'
    report_lines.append(header)
    report_lines.append(sep)

    for row in rows:
        vals = [str(row.get(c, '—')) for c in cols]
        report_lines.append('| ' + ' | '.join(vals) + ' |')

    report_lines.append('')
    report_lines.append('**评级标准**：')
    report_lines.append('- 🟢 优秀：IC>|0.08|，IR>0.5，|t|>3.0')
    report_lines.append('- 🟡 良好：IC>|0.05|，IR>0.3，|t|>2.0')
    report_lines.append('- 🟠 及格：IC>|0.02|，|t|>2.0')
    report_lines.append('- 🔴 偏弱：IC>0 但不满足上述标准')
    report_lines.append('')

    # ---- 表2: 回测评估指标 ----
    report_lines.append('## 二、单因子回测评估（持有期=5日，多空组合）')
    report_lines.append('')

    eval_header = '| 因子 | 总收益 | 年化收益 | Sharpe | 最大回撤 | Calmar | 年化Vol |'
    eval_sep = '|---|---|---:|---:|---:|---:|---:|---:|'
    report_lines.append(eval_header)
    report_lines.append(eval_sep)

    for fname, res in results.items():
        total_ret = res['total_ret'] * 100
        annual_ret = res['annual_ret'] * 100
        sharpe = res['sharpe']
        max_dd = res['max_dd'] * 100
        calmar = res['calmar']
        annual_vol = res['factor_ret'].std() * np.sqrt(252) * 100

        report_lines.append(
            f"| {fname} | {total_ret:+.2f}% | {annual_ret:+.2f}% | "
            f"{sharpe:+.3f} | {max_dd:.2f}% | {calmar:+.3f} | {annual_vol:.2f}% |"
        )

    report_lines.append('')

    # ---- 表3: IC 稳定性（年度）----
    report_lines.append('## 三、IC 稳定性（年度分解，持有期=5日）')
    report_lines.append('')

    ic_yr_header = '| 因子 | ' + ' | '.join([str(y) for y in range(2020, 2026)]) + ' |'
    ic_yr_sep = '|---|' + '|'.join(['---:'] * 6) + '|'
    report_lines.append(ic_yr_header)
    report_lines.append(ic_yr_sep)

    for fname, res in results.items():
        ic5 = res['ic_series'].get(5)
        if ic5 is None:
            report_lines.append(f"| {fname} | " + ' | '.join(['—'] * 6) + ' |')
            continue

        yearly = []
        for y in range(2020, 2026):
            yr_ic = ic5[ic5.index.year == y]
            if len(yr_ic) > 10:
                yearly.append(f"{yr_ic.mean():+.4f}")
            else:
                yearly.append('—')
        report_lines.append(f"| {fname} | " + ' | '.join(yearly) + ' |')

    report_lines.append('')

    # ---- 图表 ----
    report_lines.append('## 四、可视化')
    report_lines.append('')
    report_lines.append('### 4.1 滚动 IC 序列（60日窗口，5日前瞻）')
    report_lines.append(f'![IC Series](single_factor_IC_series.png)')
    report_lines.append('')
    report_lines.append('### 4.2 累计收益曲线（多空组合，归一化）')
    report_lines.append(f'![Equity Curves](single_factor_equity.png)')
    report_lines.append('')

    # ---- 结论 ----
    report_lines.append('## 五、结论')

    for fname, res in results.items():
        metrics_map = res['metrics']
        ic5 = metrics_map.get(5, {})
        sharpe = res['sharpe']
        max_dd = res['max_dd']
        total_ret = res['total_ret']

        rating = ic5.get('rating', '⚫ 无效') if ic5 else '⚫ 无效'
        ic_mean = ic5.get('ic_mean', 0) if ic5 else 0
        ir = ic5.get('ir', 0) if ic5 else 0
        t_stat = ic5.get('t_stat', 0) if ic5 else 0
        win_rate = ic5.get('win_rate', 0) * 100 if ic5 else 0

        verdict = ''
        if abs(ic_mean) >= 0.02 and abs(t_stat) >= 2.0 and sharpe > 0.3:
            verdict = '✅ **建议入池**'
        elif abs(ic_mean) >= 0.01 and abs(t_stat) >= 1.5:
            verdict = '🟡 **可观察**'
        else:
            verdict = '⚠️ **数据异常，谨慎评估**'

        report_lines.append(f'### {fname} ({res["factor_ret"].name})')
        report_lines.append(f'')
        report_lines.append(f'- 评级：{rating}')
        report_lines.append(f'- IC均值：{ic_mean:+.4f}（IR={ir:.3f}，t={t_stat:.2f}，胜率={win_rate:.1f}%）')
        report_lines.append(f'- 5日多空总收益：{total_ret*100:+.2f}%')
        report_lines.append(f'- Sharpe：{sharpe:.3f} | 最大回撤：{max_dd*100:.2f}% | Calmar：{res["calmar"]:.3f}')
        report_lines.append(f'- 结论：{verdict}')
        report_lines.append('')

    report_lines.append('---')
    report_lines.append(f'*由因子分析师 W4 回测框架自动生成 | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*')

    report_text = '\n'.join(report_lines)
    report_file = OUT_DIR / 'W4_single_factor_backtest_20260422.md'
    with open(report_file, 'w', encoding='utf-8-sig') as f:
        f.write(report_text)
    print(f'\n  [Report] {report_file}')

    # 保存 JSON 数据
    import json
    json_data = {}
    for fname, res in results.items():
        json_data[fname] = {
            'total_ret': float(res['total_ret']),
            'annual_ret': float(res['annual_ret']),
            'sharpe': float(res['sharpe']),
            'max_dd': float(res['max_dd']),
            'calmar': float(res['calmar']),
            'metrics': {
                fn: {k: float(v) if isinstance(v, (np.floating, np.integer)) else (bool(v) if isinstance(v, (np.bool_,)) else v)
                     for k, v in m.items()}
                for fn, m in res['metrics'].items() if m
            }
        }

    json_file = OUT_DIR / 'W4_single_factor_backtest_20260422.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f'  [JSON] {json_file}')

    return results


if __name__ == '__main__':
    results = run_backtest()
