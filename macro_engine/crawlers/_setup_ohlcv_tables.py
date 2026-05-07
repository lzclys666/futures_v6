#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_setup_ohlcv_tables.py
EC/LC OHLCV 历史数据采集 + 建表

当前状态: ✅正常
- L1: AKShare futures_main_sina(symbol='EC0'/'LC0') 获取全量历史OHLCV
- 建表: ec_futures_ohlcv / lc_futures_ohlcv（与 br_futures_ohlcv 同构）
"""
import sqlite3
import sys
import os
from datetime import datetime, date

# 项目根目录
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_PATH = os.path.join(PROJECT_ROOT, "pit_data.db")

# 确保能导入 akshare
try:
    import akshare as ak
    import pandas as pd
    print("[OK] AKShare loaded")
except ImportError:
    print("[ERR] AKShare not installed")
    sys.exit(1)

# 建表 SQL（与 br_futures_ohlcv 同构）
CREATE_OHLCV_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    pub_date   TEXT,
    obs_date   TEXT,
    contract   TEXT,
    trade_date TEXT,
    open       REAL,
    high       REAL,
    low        REAL,
    close      REAL,
    volume     INTEGER,
    hold       INTEGER,
    settle     REAL,
    PRIMARY KEY (contract, trade_date)
)
"""

# AKShare 列名映射（futures_main_sina 返回中文列名）
COL_MAP = {
    "日期": "trade_date",
    "开盘价": "open",
    "最高价": "high",
    "最低价": "low",
    "收盘价": "close",
    "成交量": "volume",
    "持仓量": "hold",
    "动态结算价": "settle",
}


def create_table(conn, table_name):
    """创建 OHLCV 表"""
    conn.execute(CREATE_OHLCV_SQL.format(table=table_name))
    conn.commit()
    print(f"[OK] Table {table_name} ready")


def fetch_and_insert(symbol, ak_symbol, table_name):
    """获取历史数据并写入"""
    print(f"\n{'='*50}")
    print(f"[{symbol}] Fetching futures_main_sina(symbol='{ak_symbol}')...")

    df = ak.futures_main_sina(symbol=ak_symbol)
    if df is None or df.empty:
        print(f"[ERR] {symbol}: empty DataFrame")
        return 0

    # 重命名列
    df = df.rename(columns=COL_MAP)
    required = ["trade_date", "open", "high", "low", "close", "volume", "hold", "settle"]
    for col in required:
        if col not in df.columns:
            print(f"[ERR] Missing column: {col}, available: {list(df.columns)}")
            return 0

    today_str = date.today().isoformat()
    contract = f"{symbol}0"  # 主力合约标记

    conn = sqlite3.connect(DB_PATH, timeout=30)
    create_table(conn, table_name)

    rows_written = 0
    for _, row in df.iterrows():
        trade_date = str(row["trade_date"])[:10]  # 只取日期部分
        try:
            conn.execute(
                f"""INSERT OR REPLACE INTO {table_name}
                    (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    today_str,
                    trade_date,
                    contract,
                    trade_date,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    int(row["volume"]),
                    int(row["hold"]),
                    float(row["settle"]),
                ),
            )
            rows_written += 1
        except Exception as e:
            print(f"[WARN] Skip row {trade_date}: {e}")

    conn.commit()

    # 验证
    cur = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    cur = conn.execute(f"SELECT MAX(trade_date) FROM {table_name}")
    latest = cur.fetchone()[0]
    conn.close()

    print(f"[OK] {symbol}: wrote {rows_written} rows, total={count}, latest={latest}")
    return count


def main():
    print(f"DB: {DB_PATH}")
    print(f"Time: {datetime.now().isoformat()}")

    results = {}

    # EC - 集运指数（上海国际能源交易中心）
    results["EC"] = fetch_and_insert("EC", "EC0", "ec_futures_ohlcv")

    # LC - 碳酸锂（广州期货交易所）
    results["LC"] = fetch_and_insert("LC", "LC0", "lc_futures_ohlcv")

    print(f"\n{'='*50}")
    print("[SUMMARY]")
    for sym, count in results.items():
        status = "OK" if count > 100 else "FAIL"
        print(f"  [{status}] {sym}: {count} rows")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
