#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_补采_OHLCV.py
用途: 创建 y_futures_ohlcv 表并补采历史 OHLCV 数据

数据源: AKShare futures_zh_daily_sina(symbol='y0')
表结构: pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle

当前状态: [✅正常]
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
import akshare as ak
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pit_data.db")


def create_table():
    """创建 y_futures_ohlcv 表"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS y_futures_ohlcv (
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
            PRIMARY KEY (contract, trade_date)
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] y_futures_ohlcv 表已创建/确认存在")


def backfill():
    """从 AKShare 补采 y0 主力合约历史 OHLCV"""
    print("[L1] AKShare futures_zh_daily_sina(symbol='y0')...")
    df = ak.futures_zh_daily_sina(symbol="y0")
    if df is None or df.empty:
        print("[ERR] 无数据")
        return 0

    pub_date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    count = 0

    for _, row in df.iterrows():
        trade_date = str(row['date']) if not isinstance(row['date'], str) else row['date']
        try:
            conn.execute("""
                INSERT OR REPLACE INTO y_futures_ohlcv
                (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_date,
                trade_date,
                "y0",
                trade_date,
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                int(row['volume']),
                int(row['hold']),
                float(row['settle'])
            ))
            count += 1
        except Exception as e:
            print(f"[WARN] 写入失败 {trade_date}: {e}")

    conn.commit()
    conn.close()
    print(f"[OK] 补采完成: {count} 条记录写入 y_futures_ohlcv")
    return count


if __name__ == "__main__":
    create_table()
    n = backfill()
    print(f"\n=== 完成: {n} 条 OHLCV 数据 ===")
