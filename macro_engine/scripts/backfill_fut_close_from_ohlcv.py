#!/usr/bin/env python3
"""从 OHLCV 表批量补写 FUT_CLOSE 因子到 pit_factor_observations（快速版）"""
import sqlite3, sys, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'D:\futures_v6\macro_engine\pit_data.db'
pub_date = datetime.now().strftime("%Y-%m-%d")

CONFIGS = [
    ('M',  'm_futures_ohlcv',  'M_FUT_CLOSE'),
    ('Y',  'y_futures_ohlcv',  'Y_FUT_CLOSE'),
    ('BU', 'bu_futures_ohlcv', 'BU_FUT_CLOSE'),
    ('EG', 'eg_futures_ohlcv', 'EG_FUT_CLOSE'),
]

conn = sqlite3.connect(DB, timeout=10)
cur = conn.cursor()

# Ensure table exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS pit_factor_observations (
        factor_code TEXT,
        symbol TEXT,
        pub_date TEXT,
        obs_date TEXT,
        raw_value REAL,
        source_confidence REAL DEFAULT 1.0,
        PRIMARY KEY (factor_code, obs_date)
    )
""")
conn.commit()

for symbol, table, factor_code in CONFIGS:
    # Check existing
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol=? AND factor_code=?", (symbol, factor_code))
    existing = cur.fetchone()[0]
    # Read OHLCV count
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    ohlcv_count = cur.fetchone()[0]
    if existing >= ohlcv_count:
        print(f"[SKIP] {factor_code}: already {existing}/{ohlcv_count} rows")
        continue
    print(f"[INFO] {factor_code}: {existing}/{ohlcv_count} rows,补写中...")

    # Read OHLCV
    cur.execute(f"SELECT trade_date, close FROM {table} ORDER BY trade_date")
    rows = cur.fetchall()
    if not rows:
        print(f"[WARN] {table}: no data")
        continue

    # Batch insert
    data = []
    for trade_date, close_val in rows:
        if close_val is None or close_val <= 0:
            continue
        data.append((factor_code, symbol, pub_date, trade_date, float(close_val), 1.0))

    cur.executemany("""
        INSERT OR REPLACE INTO pit_factor_observations
        (factor_code, symbol, pub_date, obs_date, raw_value, source_confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    print(f"[OK] {factor_code}: {len(data)} records written")

conn.close()
print("\n=== DONE ===")
