"""
compute_ic_heatmap.py

基于 pit_factor_observations 表，计算各品种、各因子的 IC 值。

数据来源：
- pit_factor_observations: 因子观测值
- {symbol}_futures_ohlcv（单品种表）或 jm_futures_ohlcv（多品种混合表）：价格数据

算法：
1. 对每个 (symbol, factor_code) 组合，取 obs_date 对齐的因子序列
2. 对应的价格收益率序列：取次日收益率 pct_change().shift(-1)
3. 计算 60 日滚动 Spearman 相关系数（IC）
4. 计算 IR = IC_mean / IC_std 和符号稳定性

注意：
- 只对已有足够样本（>=30 条 obs）的 (factor, symbol) 计算真实 IC
- 样本不足 <60 条的标记 is_mock=1
- 价格表用 contract LIKE '{SYMBOL}%' 筛选，不用 symbol 列
"""

import sqlite3
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
from pathlib import Path
from scipy import stats

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

# 已知有独立 OHLCV 表的品种（其他品种从 jm_futures_ohlcv 获取价格）
OWN_OHLCV_SYMBOLS = {"AG", "AU", "CU", "NI", "RB", "RU", "ZN", "JM"}


def get_ohlcv_table(symbol: str) -> str | None:
    """返回品种对应的 OHLCV 表名，没有则返回 None（用 jm_futures_ohlcv）"""
    table = f"{symbol.lower()}_futures_ohlcv"
    if symbol in OWN_OHLCV_SYMBOLS:
        return table
    return None


def get_main_contract(cursor, symbol: str, ohlcv_table: str) -> str | None:
    """
    获取品种的主力合约代码（如 'CU888'）。
    逻辑：找 contract 形如 '{SYMBOL}88' 或 '{SYMBOL}888' 的主连合约；
    如果不存在，取 obs_date 最新的一条记录对应的 contract。
    """
    # 品种到合约前缀的映射（用于 jm_futures_ohlcv 等混合表）
    SYMBOL_TO_PREFIX = {
        'J': 'JM',   # 焦炭在 jm_futures_ohlcv 表中以 JM 开头
        'JM': 'JM',
        'I': 'I',    # 铁矿石
        'HC': 'HC',
        'RB': 'RB',
        'NI': 'NI',
    }

    # 当 fallback 到 jm_futures_ohlcv 时，使用正确的合约前缀
    effective_symbol = SYMBOL_TO_PREFIX.get(symbol, symbol)

    # 先尝试找主连合约（带 '88' 后缀的）
    cursor.execute(f"""
        SELECT DISTINCT contract FROM {ohlcv_table}
        WHERE contract LIKE '{effective_symbol}8%'
        ORDER BY contract
    """)
    contracts = [r[0] for r in cursor.fetchall()]
    if contracts:
        # 优先 CU888 类
        main = next((c for c in contracts if c == f"{effective_symbol}888"), None)
        if not main:
            main = next((c for c in contracts if c.endswith('8')), None)
        if not main:
            main = contracts[-1]
        return main

    # 回退：取 obs_date 最大的那条
    cursor.execute(f"""
        SELECT contract FROM {ohlcv_table}
        ORDER BY obs_date DESC LIMIT 1
    """)
    row = cursor.fetchone()
    return row[0] if row else None


def get_price_returns(symbol: str) -> pd.Series:
    """获取品种次日收益率序列"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 确定价格表
    ohlcv_table = get_ohlcv_table(symbol)
    if ohlcv_table is None:
        ohlcv_table = "jm_futures_ohlcv"
        # J（焦炭）的合约在 jm_futures_ohlcv 表中以 'JM' 开头
        contract_prefix = "JM" if symbol == "J" else symbol
        where = f"WHERE contract LIKE '{contract_prefix}%'"
    else:
        where = ""

    # 确认表存在
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (ohlcv_table,)
    )
    if not cursor.fetchone():
        conn.close()
        return pd.Series(dtype=float)

    # 获取主力合约
    contract = get_main_contract(cursor, symbol, ohlcv_table)
    if not contract:
        conn.close()
        return pd.Series(dtype=float)

    # 查询价格数据（按合约过滤）
    df = pd.read_sql_query(f"""
        SELECT obs_date, close
        FROM {ohlcv_table}
        WHERE contract = ?
        ORDER BY obs_date
    """, conn, params=(contract,))
    conn.close()

    if df.empty:
        return pd.Series(dtype=float)

    df['obs_date'] = pd.to_datetime(df['obs_date'])
    df = df.set_index('obs_date').sort_index()

    # 去重（同日期多条记录取最后一条）
    df = df[~df.index.duplicated(keep='last')]

    # 次日收益率：shift(-1) = 今日收盘买入，次日收盘卖出的收益率
    df['return_1d'] = df['close'].pct_change().shift(-1)
    return df['return_1d'].dropna()


def get_factor_series(factor_code: str, symbol: str) -> pd.Series:
    """获取因子时间序列"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT obs_date, raw_value
        FROM pit_factor_observations
        WHERE factor_code = ? AND symbol = ?
        ORDER BY obs_date
    """, conn, params=(factor_code, symbol))
    conn.close()

    if df.empty:
        return pd.Series(dtype=float)

    df['obs_date'] = pd.to_datetime(df['obs_date'])
    df = df.set_index('obs_date').sort_index()

    # 去重（同日期多条记录取第一条）
    df = df[~df.index.duplicated(keep='first')]

    return df['raw_value']


def calculate_ic(factor_series: pd.Series, return_series: pd.Series, window: int = 60):
    """
    计算 60 日滚动 IC 均值、IR 和符号稳定性。

    参数：
        factor_series: 因子值序列（日期索引）
        return_series: 次日收益率序列（日期索引）
        window: 滚动窗口大小，默认 60 天

    返回：
        (ic_mean, ir, sign_stability) 或 (None, 0, 0) 如果样本不足
    """
    # 对齐索引
    common_idx = factor_series.index.intersection(return_series.index)
    if len(common_idx) < 30:
        return None, 0.0, 0.0

    f = factor_series.loc[common_idx].reset_index(drop=True)
    r = return_series.loc[common_idx].reset_index(drop=True)

    # 滚动 IC（从第 window 天开始）
    ic_values = []
    for i in range(window, len(f)):
        ic, _ = stats.spearmanr(f.iloc[i - window:i], r.iloc[i - window:i])
        ic_values.append(ic)

    if not ic_values:
        return None, 0.0, 0.0

    ic_arr = np.array(ic_values)
    ic_mean = float(np.nanmean(ic_arr))
    ic_std = float(np.nanstd(ic_arr))
    ir = ic_mean / ic_std if ic_std > 0 else 0.0

    # 符号稳定性：60 日窗口内 IC 符号一致的比例
    signs = np.sign(ic_arr)
    sign_stability = float((signs == signs[0]).mean())

    return ic_mean, ir, sign_stability


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default=None, help='只计算指定品种')
    args = parser.parse_args()

    calc_date = datetime.now().strftime("%Y-%m-%d")

    # 获取所有 (symbol, factor_code) 组合
    conn = sqlite3.connect(DB_PATH)
    if args.symbol:
        df_meta = pd.read_sql_query("""
            SELECT DISTINCT factor_code, symbol
            FROM pit_factor_observations
            WHERE symbol = ?
            ORDER BY symbol, factor_code
        """, conn, params=(args.symbol,))
    else:
        df_meta = pd.read_sql_query("""
            SELECT DISTINCT factor_code, symbol
            FROM pit_factor_observations
            ORDER BY symbol, factor_code
        """, conn)
    conn.close()

    results = []
    skipped_no_price = []
    skipped_no_factor = []

    for _, row in df_meta.iterrows():
        factor_code = row['factor_code']
        symbol = row['symbol']

        factor_series = get_factor_series(factor_code, symbol)
        if len(factor_series) < 30:
            skipped_no_factor.append(f"{symbol}/{factor_code}")
            continue

        price_returns = get_price_returns(symbol)
        if len(price_returns) < 30:
            skipped_no_price.append(symbol)
            continue

        # 窗口自适应：共同日期不足 60 时降至 30
        window = 60
        if args.symbol and len(factor_series) < 60:
            window = 30
        # 窗口自适应：共同日期不足 60 时降至 30
        common_idx = factor_series.index.intersection(price_returns.index)
        window = 60 if len(common_idx) >= 60 else 30
        ic_mean, ir, sign_stability = calculate_ic(factor_series, price_returns, window=window)
        if ic_mean is None:
            continue

        # 样本 < 60 条标记为模拟数据
        is_mock = 1 if len(factor_series) < 60 else 0

        # target_symbol: 收益目标品种，默认与 symbol 相同（同品种 IC）
        # 未来可扩展为跨品种 IC（如 DXY -> AG），在 symbol x target_symbol 笛卡尔积上计算
        target_symbol = symbol

        results.append({
            'calc_date': calc_date,
            'symbol': symbol,
            'factor': factor_code,
            'ic_value': round(ic_mean, 4),
            'samples': int(len(factor_series)),
            'is_mock': is_mock,
            'ir': round(ir, 4),
            'sign_stability': round(sign_stability, 4),
            'target_symbol': target_symbol,
        })

    if not results:
        print("警告：无有效 IC 结果（所有品种-因子组合都没有足够的共同交易日数据）")
        return

    # 写入 ic_heatmap 表
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for r in results:
        cursor.execute("""
            INSERT OR REPLACE INTO ic_heatmap
            (calc_date, symbol, factor, ic_value, samples, is_mock, ir, sign_stability, target_symbol)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['calc_date'], r['symbol'], r['factor'],
            r['ic_value'], r['samples'], r['is_mock'],
            r['ir'], r['sign_stability'], r['target_symbol']
        ))

    conn.commit()
    conn.close()

    # 摘要输出
    samples_vals = [r['samples'] for r in results]
    ic_vals = [r['ic_value'] for r in results]
    ir_vals = [r['ir'] for r in results]
    ss_vals = [r['sign_stability'] for r in results]

    print(f"计算完成：{len(results)} 个 (品种, 因子) 组合")
    print(f"样本量：最小={min(samples_vals)}, 最大={max(samples_vals)}, 中位数={np.median(samples_vals):.0f}")
    print(f"IC 均值={np.mean(ic_vals):.4f}, 最大={max(ic_vals):.4f}, 最小={min(ic_vals):.4f}")
    print(f"IR 均值={np.mean(ir_vals):.4f}, 最大={max(ir_vals):.4f}, 最小={min(ir_vals):.4f}")
    print(f"符号稳定性 均值={np.mean(ss_vals):.4f}")
    print(f"ic_heatmap 表写入 {len(results)} 条记录")

    if skipped_no_price:
        unique_skipped = sorted(set(skipped_no_price))
        print(f"\n跳过（无价格数据）：{unique_skipped}")

    # 验收：ic_heatmap 表行数 & target_symbol 分布
    conn2 = sqlite3.connect(DB_PATH)
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT COUNT(*) FROM ic_heatmap")
    total_rows = cursor2.fetchone()[0]
    cursor2.execute("SELECT target_symbol, COUNT(*) FROM ic_heatmap GROUP BY target_symbol ORDER BY COUNT(*) DESC")
    dist = cursor2.fetchall()
    conn2.close()
    print(f"\n=== 验收 ===")
    print(f"ic_heatmap 表总行数: {total_rows}")
    print("target_symbol 分布:")
    for ts, cnt in dist:
        print(f"  {ts}: {cnt}")
    # 检查新写入数据 target_symbol 非 NULL
    null_count = next(((ts, cnt) for ts, cnt in dist if ts is None), None)
    if null_count:
        print(f"警告: ic_heatmap 中有 {null_count[1]} 条 target_symbol 为 NULL")
    else:
        print("[OK] 新写入数据 target_symbol 非 NULL")


if __name__ == "__main__":
    main()