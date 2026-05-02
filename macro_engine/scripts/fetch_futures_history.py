#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货历史价格数据采集脚本
使用 AKShare 获取期货历史日线数据，存入 pit_data.db

用法:
    python fetch_futures_history.py --symbol JM --days 252
    python fetch_futures_history.py --symbol RU --start 2025-01-01 --end 2026-04-27
    python fetch_futures_history.py --all  # 采集所有配置品种
"""

import sys
import os
import argparse
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import akshare as ak
except ImportError:
    print("[错误] 未安装 AKShare，请运行: pip install akshare")
    sys.exit(1)

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "pit_data.db"

# 品种代码映射（AKShare 合约代码）
SYMBOL_MAP = {
    "RU": "RU0",      # 橡胶主力
    "JM": "JM0",      # 焦煤主力
    "J": "J0",        # 焦炭主力
    "RB": "RB0",      # 螺纹钢主力
    "HC": "HC0",      # 热卷主力
    "I": "I0",        # 铁矿石主力
    "CU": "CU0",      # 沪铜主力
    "ZN": "ZN0",      # 沪锌主力
    "AL": "AL0",      # 沪铝主力
    "NI": "NI0",      # 沪镍主力
    "AU": "AU0",      # 沪金主力
    "AG": "AG0",      # 沪银主力
    "SC": "SC0",      # 原油主力
    "TA": "TA0",      # PTA主力
    "MA": "MA0",      # 甲醇主力
    "PP": "PP0",      # 聚丙烯主力
    "L": "L0",        # 塑料主力
    "EG": "EG0",      # 乙二醇主力
    "BU": "BU0",      # 沥青主力
    "FU": "FU0",      # 燃料油主力
    "SA": "SA0",      # 纯碱主力
    "FG": "FG0",      # 玻璃主力
}


def ensure_ohlcv_table(symbol: str):
    """确保价格表存在（按品种动态建表）"""
    table_name = f"{symbol.lower()}_futures_ohlcv"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            pub_date TEXT,
            obs_date TEXT,
            contract TEXT,
            trade_date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            hold INTEGER,
            settle REAL,
            PRIMARY KEY (obs_date, contract)
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DB] 确保表存在: {table_name}")


def fetch_futures_history(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取期货历史数据
    
    :param symbol: 品种代码（如 JM）
    :param start_date: 开始日期（YYYY-MM-DD）
    :param end_date: 结束日期（YYYY-MM-DD）
    :return: DataFrame with columns: date, open, high, low, close, volume, hold
    """
    ak_symbol = SYMBOL_MAP.get(symbol, f"{symbol}0")
    
    print(f"[AKShare] 获取 {symbol} ({ak_symbol}) 历史数据: {start_date} ~ {end_date}")
    
    try:
        # 使用 AKShare 获取期货主力合约历史数据
        df = ak.futures_main_sina(symbol=ak_symbol, start_date=start_date, end_date=end_date)
        
        if df is None or df.empty:
            print(f"[警告] {symbol} 返回空数据")
            return pd.DataFrame()
        
        print(f"[AKShare] 获取到 {len(df)} 条记录")
        print(f"[AKShare] 列名: {df.columns.tolist()}")
        
        return df
        
    except Exception as e:
        print(f"[错误] 获取 {symbol} 数据失败: {e}")
        return pd.DataFrame()


def save_to_db(symbol: str, df: pd.DataFrame):
    """
    保存数据到数据库
    
    :param symbol: 品种代码
    :param df: DataFrame with historical data
    """
    if df.empty:
        return
    
    table_name = f"{symbol.lower()}_futures_ohlcv"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取今天日期作为 pub_date
    pub_date = datetime.now().strftime("%Y-%m-%d")
    
    inserted = 0
    
    # AKShare 返回的列名（中文，但可能有编码问题）
    # 列顺序: 日期, 开盘价, 最高价, 最低价, 收盘价, 成交量, 持仓量, 动态结算价
    cols = df.columns.tolist()
    
    for _, row in df.iterrows():
        try:
            # 解析日期（第一列）
            trade_date = pd.to_datetime(row.iloc[0])
            obs_date = trade_date.strftime("%Y-%m-%d")
            
            # 合约代码（使用主力合约）
            contract = f"{symbol}0"
            
            # 提取价格数据（按索引，避免中文编码问题）
            open_price = float(row.iloc[1]) if len(row) > 1 else 0
            high_price = float(row.iloc[2]) if len(row) > 2 else 0
            low_price = float(row.iloc[3]) if len(row) > 3 else 0
            close_price = float(row.iloc[4]) if len(row) > 4 else 0
            volume = int(row.iloc[5]) if len(row) > 5 else 0
            hold = int(row.iloc[6]) if len(row) > 6 else 0
            settle = float(row.iloc[7]) if len(row) > 7 else close_price
            
            # 插入或更新（动态表名）
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name}
                (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_date, obs_date, contract, obs_date,
                open_price, high_price, low_price, close_price,
                volume, hold, settle
            ))
            
            inserted += 1
            
        except Exception as e:
            print(f"[警告] 处理行失败: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"[DB] 保存完成: {table_name} 共 {inserted} 条记录")


def get_db_date_range(symbol: str) -> tuple:
    """
    获取数据库中已有数据的日期范围
    
    :return: (min_date, max_date) or (None, None)
    """
    table_name = f"{symbol.lower()}_futures_ohlcv"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 先检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        return None, None
    
    cursor.execute(f"""
        SELECT MIN(obs_date), MAX(obs_date) 
        FROM {table_name}
        WHERE contract LIKE ?
    """, (f"{symbol}%",))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return result[0], result[1]
    return None, None


def main():
    parser = argparse.ArgumentParser(description='期货历史价格数据采集')
    parser.add_argument('--symbol', type=str, help='品种代码（如 JM, RU, RB）')
    parser.add_argument('--days', type=int, default=252, help='采集天数（默认252个交易日≈1年）')
    parser.add_argument('--start', type=str, help='开始日期（YYYY-MM-DD）')
    parser.add_argument('--end', type=str, help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--all', action='store_true', help='采集所有配置品种')
    
    args = parser.parse_args()
    
    # 确保表存在（延迟到采集时按品种建表）
    
    # 计算日期范围
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    elif args.days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days * 1.5)).strftime("%Y-%m-%d")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    # 确定采集品种列表
    if args.all:
        symbols = list(SYMBOL_MAP.keys())
    elif args.symbol:
        symbols = [args.symbol.upper()]
    else:
        print("[错误] 请指定 --symbol 或 --all")
        parser.print_help()
        sys.exit(1)
    
    print(f"=" * 60)
    print(f"期货历史价格数据采集")
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"品种数量: {len(symbols)}")
    print(f"=" * 60)
    
    # 采集数据
    total_records = 0
    success_symbols = []
    failed_symbols = []
    
    for symbol in symbols:
        print(f"\n{'='*40}")
        print(f"采集: {symbol}")
        print(f"{'='*40}")
        
        # 确保表存在（按品种动态建表）
        ensure_ohlcv_table(symbol)

        # 检查已有数据
        min_date, max_date = get_db_date_range(symbol)
        if min_date and max_date:
            print(f"[DB] 已有数据: {min_date} ~ {max_date}")
        
        # 获取数据
        df = fetch_futures_history(symbol, start_date, end_date)
        
        if not df.empty:
            # 保存到数据库
            save_to_db(symbol, df)
            total_records += len(df)
            success_symbols.append(symbol)
        else:
            failed_symbols.append(symbol)
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"采集完成")
    print(f"{'='*60}")
    print(f"成功: {len(success_symbols)} 个品种")
    if success_symbols:
        print(f"  {', '.join(success_symbols)}")
    print(f"失败: {len(failed_symbols)} 个品种")
    if failed_symbols:
        print(f"  {', '.join(failed_symbols)}")
    print(f"总记录数: {total_records}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
