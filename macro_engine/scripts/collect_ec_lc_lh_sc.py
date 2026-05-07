#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补采 EC/LC/LH/SC 因子数据（精简版）
目标：从2个有效因子 → ≥7个（FUT_CLOSE, FUT_OI, SPD_01, SPD_03, SPD_05, POS_OI, POS_CHANGE）

步骤：
1. 创建 spread 表 → 采集月差数据
2. 创建 hold_volume 表 → 采集持仓量数据
3. 聚合新因子到 pit_factor_observations
"""
import sqlite3
import logging
import time
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd

DB_PATH = Path(r"D:\futures_v6\macro_engine\pit_data.db")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 品种配置
SYMBOL_CONFIG = {
    "EC": {
        "name": "集运指数(欧线)",
        "main": "EC2508",
        "spread_contracts": {"near": "EC2506", "m3": "EC2510", "m5": "EC2512"},
        "hold_contracts": ["EC2506", "EC2508", "EC2510", "EC2512"],
    },
    "LC": {
        "name": "碳酸锂",
        "main": "LC2507",
        "spread_contracts": {"near": "LC2506", "m3": "LC2509", "m5": "LC2511"},
        "hold_contracts": ["LC2506", "LC2507", "LC2509", "LC2511"],
    },
    "LH": {
        "name": "生猪",
        "main": "LH2509",
        "spread_contracts": {"near": "LH2507", "m3": "LH2511", "m5": "LH2601"},
        "hold_contracts": ["LH2507", "LH2509", "LH2511", "LH2601"],
    },
    "SC": {
        "name": "原油",
        "main": "SC2508",
        "spread_contracts": {"near": "SC2506", "m3": "SC2510", "m5": "SC2512"},
        "hold_contracts": ["SC2506", "SC2508", "SC2510", "SC2512"],
    },
}

SOURCE = "aggregated"
CONFIDENCE = 0.85


def fetch_contract(contract: str) -> pd.DataFrame:
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        for col in ['open', 'high', 'low', 'close', 'settle', 'hold', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        logger.error(f"  fetch {contract}: {e}")
        return pd.DataFrame()


def collect_spread(sym: str, conn) -> int:
    cfg = SYMBOL_CONFIG[sym]
    main = cfg["main"]
    table = f"{sym.lower()}_futures_spread"
    
    # 创建表
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
        pub_date TEXT, obs_date TEXT, trade_date TEXT,
        spread_01 REAL, spread_03 REAL, spread_05 REAL,
        PRIMARY KEY (pub_date, trade_date)
    )""")
    
    logger.info(f"[{sym}] Fetching spread: {main} vs {list(cfg['spread_contracts'].values())}")
    main_df = fetch_contract(main)
    if main_df.empty:
        logger.error(f"[{sym}] No data for {main}")
        return 0
    
    result = main_df[['date', 'settle']].rename(columns={'settle': 'main_settle'})
    for label, contract in cfg['spread_contracts'].items():
        df = fetch_contract(contract)
        if not df.empty:
            sub = df[['date', 'settle']].rename(columns={'settle': f'{label}_settle'})
            result = result.merge(sub, on='date', how='outer')
        else:
            logger.warning(f"  {contract}: no data")
        time.sleep(0.3)
    
    result = result.sort_values('date').reset_index(drop=True)
    pub_date = datetime.now().strftime('%Y-%m-%d')
    written = 0
    
    for _, row in result.iterrows():
        vals = {}
        for label, sname in [("near", "spread_01"), ("m3", "spread_03"), ("m5", "spread_05")]:
            col = f'{label}_settle'
            if col in result.columns and pd.notna(row.get(col)) and pd.notna(row.get('main_settle')):
                vals[sname] = float(row['main_settle']) - float(row[col])
            else:
                vals[sname] = None
        
        conn.execute(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?,?,?,?)",
                     (pub_date, row['date'], row['date'],
                      vals.get('spread_01'), vals.get('spread_03'), vals.get('spread_05')))
        written += 1
    
    conn.commit()
    logger.info(f"[{sym}] Spread: {written} rows -> {table}")
    return written


def collect_hold_volume(sym: str, conn) -> int:
    cfg = SYMBOL_CONFIG[sym]
    table = f"{sym.lower()}_futures_hold_volume"
    
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
        pub_date TEXT, obs_date TEXT, contract TEXT, trade_date TEXT,
        hold_volume REAL, hold_change REAL, volume REAL,
        PRIMARY KEY (pub_date, contract, trade_date)
    )""")
    
    logger.info(f"[{sym}] Fetching hold_volume for {cfg['hold_contracts']}")
    all_data = []
    for c in cfg['hold_contracts']:
        df = fetch_contract(c)
        if df.empty:
            logger.warning(f"  {c}: no data")
            continue
        df['contract'] = c
        df['hold_change'] = df['hold'].diff()
        all_data.append(df[['date', 'contract', 'hold', 'hold_change', 'volume']])
        logger.info(f"  {c}: {len(df)} rows")
        time.sleep(0.3)
    
    if not all_data:
        return 0
    
    combined = pd.concat(all_data, ignore_index=True)
    pub_date = datetime.now().strftime('%Y-%m-%d')
    written = 0
    
    for _, row in combined.iterrows():
        conn.execute(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?,?,?,?,?)",
                     (pub_date, row['date'], row['contract'], row['date'],
                      int(row['hold']) if pd.notna(row['hold']) else None,
                      int(row['hold_change']) if pd.notna(row['hold_change']) else None,
                      int(row['volume']) if pd.notna(row['volume']) else None))
        written += 1
    
    conn.commit()
    logger.info(f"[{sym}] Hold_volume: {written} rows -> {table}")
    return written


def aggregate_new_factors(sym: str, conn) -> int:
    """将 spread/hold_volume 数据聚合到 pit_factor_observations（仅新因子代码）"""
    cur = conn.cursor()
    written = 0
    pub_date = datetime.now().strftime('%Y-%m-%d')
    
    # Spread → SPD_01, SPD_03, SPD_05
    spread_table = f"{sym.lower()}_futures_spread"
    try:
        for scol, fname in [("spread_01", f"{sym}_SPD_01"), 
                             ("spread_03", f"{sym}_SPD_03"),
                             ("spread_05", f"{sym}_SPD_05")]:
            cur.execute(f"SELECT trade_date, {scol} FROM {spread_table} WHERE {scol} IS NOT NULL")
            for trade_date, val in cur.fetchall():
                if trade_date != pub_date:  # PIT
                    cur.execute("""
                        INSERT OR REPLACE INTO pit_factor_observations
                        (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (fname, sym, pub_date, trade_date, float(val), SOURCE, CONFIDENCE))
                    written += 1
    except Exception as e:
        logger.warning(f"[{sym}] Spread aggregate: {e}")
    
    # Hold_volume → POS_OI, POS_CHANGE
    hold_table = f"{sym.lower()}_futures_hold_volume"
    try:
        cur.execute(f"""
            SELECT trade_date, SUM(hold_volume), SUM(hold_change)
            FROM {hold_table} WHERE hold_volume IS NOT NULL
            GROUP BY trade_date
        """)
        for trade_date, total_oi, total_chg in cur.fetchall():
            if trade_date != pub_date:
                cur.execute("""
                    INSERT OR REPLACE INTO pit_factor_observations
                    (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (f"{sym}_POS_OI", sym, pub_date, trade_date, float(total_oi), SOURCE, CONFIDENCE))
                written += 1
                if total_chg is not None:
                    cur.execute("""
                        INSERT OR REPLACE INTO pit_factor_observations
                        (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (f"{sym}_POS_CHANGE", sym, pub_date, trade_date, float(total_chg), SOURCE, CONFIDENCE))
                    written += 1
    except Exception as e:
        logger.warning(f"[{sym}] Hold aggregate: {e}")
    
    conn.commit()
    logger.info(f"[{sym}] Aggregated {written} new factor records")
    return written


def main():
    logger.info("=" * 60)
    logger.info("EC/LC/LH/SC 因子数据补采（精简版）")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    results = {}
    for sym in SYMBOL_CONFIG:
        logger.info(f"\n--- {sym} ({SYMBOL_CONFIG[sym]['name']}) ---")
        n_spread = collect_spread(sym, conn)
        n_hold = collect_hold_volume(sym, conn)
        n_pit = aggregate_new_factors(sym, conn)
        results[sym] = {"spread": n_spread, "hold": n_hold, "pit": n_pit}
    
    conn.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    for sym, r in results.items():
        logger.info(f"  {sym}: spread={r['spread']}, hold={r['hold']}, pit_records={r['pit']}")
    logger.info("DONE")


if __name__ == "__main__":
    main()
