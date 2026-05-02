#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IC (Information Coefficient) 热力图数据计算脚本

计算各品种、各因子的 IC 值，用于前端热力图展示

用法:
    python calculate_ic_heatmap.py
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from scipy import stats

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "pit_data.db"

# 品种列表
SYMBOLS = ["JM", "RU", "RB", "ZN", "NI"]

# 因子配置（表名、数值列、是否有合约列）
FACTOR_CONFIG = {
    "basis": {
        "table": "jm_futures_basis",
        "value_col": "basis_rate",
        "has_contract": True,
    },
    "spread": {
        "table": "jm_futures_spread",
        "value_col": "spread_01",
        "has_contract": False,
    },
    "hold_volume": {
        "table": "jm_futures_hold_volume",
        "value_col": "hold_volume",
        "has_contract": True,
    },
    "basis_volatility": {
        "table": "jm_basis_volatility",
        "value_col": "basis_vol_20d",
        "has_contract": False,
    },
    "import": {
        "table": "jm_import_monthly",
        "value_col": "import_volume",
        "has_contract": False,
    },
}


def get_price_data(symbol: str, days: int = 252) -> pd.DataFrame:
    """获取价格数据"""
    conn = sqlite3.connect(DB_PATH)
    
    query = f"""
        SELECT obs_date, close, volume
        FROM jm_futures_ohlcv
        WHERE contract = '{symbol}0'
        ORDER BY obs_date
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    df['obs_date'] = pd.to_datetime(df['obs_date'])
    df = df.set_index('obs_date').sort_index()
    
    # 计算收益率（次日）
    df['return_1d'] = df['close'].pct_change().shift(-1)
    
    return df


def get_factor_data(config: dict, symbol: str, days: int = 252) -> pd.DataFrame:
    """获取因子数据"""
    table = config["table"]
    value_col = config["value_col"]
    has_contract = config["has_contract"]
    
    conn = sqlite3.connect(DB_PATH)
    
    # 检查表是否存在
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if not cursor.fetchone():
        conn.close()
        return pd.DataFrame()
    
    # 构建查询
    if has_contract:
        where_clause = f"WHERE contract LIKE '{symbol}%'"
    else:
        where_clause = ""
    
    query = f"""
        SELECT obs_date, {value_col} as value
        FROM {table}
        {where_clause}
        ORDER BY obs_date
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"  [错误] 查询失败: {e}")
        conn.close()
        return pd.DataFrame()
    
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    df['obs_date'] = pd.to_datetime(df['obs_date'])
    df = df.set_index('obs_date').sort_index()
    
    # 处理重复日期（取平均值）
    df = df.groupby(df.index).mean(numeric_only=True)
    
    # 删除 NULL 值
    df = df.dropna()
    
    return df


def calculate_ic(factor_series: pd.Series, return_series: pd.Series) -> float:
    """
    计算 IC 值（秩相关系数）
    
    IC = corr(rank(factor), rank(return))
    """
    # 对齐数据
    aligned = pd.concat([factor_series, return_series], axis=1).dropna()
    
    if len(aligned) < 30:  # 最少需要30个样本
        return np.nan
    
    factor_rank = aligned.iloc[:, 0].rank()
    return_rank = aligned.iloc[:, 1].rank()
    
    # 计算斯皮尔曼秩相关系数
    ic, _ = stats.spearmanr(factor_rank, return_rank)
    
    return ic


def generate_mock_ic(symbol: str, factor: str) -> float:
    """
    生成模拟 IC 值（用于前端展示）
    
    基于品种和因子特性生成合理的 IC 值范围
    """
    # 设置随机种子以确保可重复性
    np.random.seed(hash(f"{symbol}_{factor}") % 2**32)
    
    # 不同因子的典型 IC 范围
    factor_ranges = {
        "basis": (-0.15, 0.25),      # 基差因子通常有正向预测能力
        "spread": (-0.10, 0.20),     # 价差因子
        "hold_volume": (-0.20, 0.15), # 持仓量因子
        "basis_volatility": (-0.15, 0.10), # 基差波动率
        "import": (-0.10, 0.15),     # 进口量因子
    }
    
    range_min, range_max = factor_ranges.get(factor, (-0.15, 0.15))
    
    # 生成 IC 值（偏向正值，表示有预测能力）
    ic = np.random.uniform(range_min, range_max)
    
    return round(ic, 4)


def calculate_ic_heatmap():
    """计算 IC 热力图数据"""
    print("=" * 60)
    print("IC 热力图数据计算")
    print("=" * 60)
    
    results = []
    
    for symbol in SYMBOLS:
        print(f"\n处理品种: {symbol}")
        
        # 获取价格数据
        price_df = get_price_data(symbol)
        if price_df.empty:
            print(f"  [警告] {symbol} 无价格数据")
            continue
        
        print(f"  价格数据: {len(price_df)} 条")
        
        for factor_name, config in FACTOR_CONFIG.items():
            # 获取因子数据
            factor_df = get_factor_data(config, symbol)
            
            if factor_df.empty or len(factor_df) < 30:
                # 数据不足，使用模拟 IC
                ic = generate_mock_ic(symbol, factor_name)
                samples = 0
                is_mock = True
                print(f"  {factor_name}: IC={ic:.4f} (模拟数据)")
            else:
                # 计算真实 IC
                ic = calculate_ic(factor_df['value'], price_df['return_1d'])
                samples = min(len(factor_df), len(price_df))
                is_mock = False
                print(f"  {factor_name}: IC={ic:.4f} (样本数={samples})")
            
            results.append({
                'symbol': symbol,
                'factor': factor_name,
                'ic': ic,
                'samples': samples,
                'is_mock': is_mock,
            })
    
    # 保存结果
    if results:
        results_df = pd.DataFrame(results)
        save_ic_results(results_df)
        print("\n" + "=" * 60)
        print("IC 热力图数据计算完成")
        print("=" * 60)
        print_ic_heatmap(results_df)
    else:
        print("\n[错误] 无有效结果")


def save_ic_results(df: pd.DataFrame):
    """保存 IC 结果到数据库"""
    conn = sqlite3.connect(DB_PATH)
    
    # 删除旧表（如果存在）
    conn.execute("DROP TABLE IF EXISTS ic_heatmap")
    
    # 创建 IC 结果表
    conn.execute("""
        CREATE TABLE ic_heatmap (
            calc_date TEXT,
            symbol TEXT,
            factor TEXT,
            ic_value REAL,
            samples INTEGER,
            is_mock INTEGER,
            PRIMARY KEY (calc_date, symbol, factor)
        )
    """)
    
    calc_date = datetime.now().strftime("%Y-%m-%d")
    
    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO ic_heatmap (calc_date, symbol, factor, ic_value, samples, is_mock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (calc_date, row['symbol'], row['factor'], row['ic'], row['samples'], 1 if row['is_mock'] else 0))
    
    conn.commit()
    conn.close()
    
    print(f"\n[DB] 保存 {len(df)} 条 IC 结果")


def print_ic_heatmap(df: pd.DataFrame):
    """打印 IC 热力图"""
    print("\nIC 热力图:")
    print("-" * 70)
    
    # 透视表
    pivot = df.pivot(index='symbol', columns='factor', values='ic')
    
    print(f"{'品种':<6} {'basis':<10} {'spread':<10} {'hold_volume':<12} {'basis_volatility':<16} {'import':<10}")
    print("-" * 70)
    
    for symbol in pivot.index:
        row = pivot.loc[symbol]
        print(f"{symbol:<6} {row.get('basis', np.nan):<10.4f} {row.get('spread', np.nan):<10.4f} "
              f"{row.get('hold_volume', np.nan):<12.4f} {row.get('basis_volatility', np.nan):<16.4f} "
              f"{row.get('import', np.nan):<10.4f}")
    
    print("-" * 70)
    print("\n注: 部分数据为模拟值（因子数据不足），用于前端展示")


if __name__ == "__main__":
    calculate_ic_heatmap()
