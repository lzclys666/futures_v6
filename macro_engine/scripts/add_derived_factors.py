#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 EC/LC/LH/SC 补充派生因子（从现有 FUT_CLOSE 计算）
目标：7 → 12 factors（FUT_RETURN_1D, FUT_RETURN_5D, FUT_VOL_20D, FUT_HIGH_20D, FUT_LOW_20D）
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import numpy as np

DB_PATH = Path(r"D:\futures_v6\macro_engine\pit_data.db")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SOURCE = "derived"
CONFIDENCE = 0.80
PUB_DATE = datetime.now().strftime('%Y-%m-%d')

SYMBOLS = ['EC', 'LC', 'LH', 'SC', 'PP', 'SN', 'M', 'Y', 'BU', 'EG']


def compute_derived_factors(sym: str, conn) -> int:
    """从 FUT_CLOSE 计算派生因子"""
    cur = conn.cursor()
    written = 0
    
    # 获取现有的 FUT_CLOSE 数据（使用最新的 pub_date）
    rows = cur.execute("""
        SELECT obs_date, raw_value FROM pit_factor_observations
        WHERE symbol = ? AND factor_code = ?
        ORDER BY obs_date
    """, (sym, f"{sym}_FUT_CLOSE")).fetchall()
    
    if len(rows) < 25:
        logger.warning(f"[{sym}] Only {len(rows)} FUT_CLOSE rows, need ≥25 for derived factors")
        return 0
    
    dates = [r[0] for r in rows]
    closes = np.array([r[1] for r in rows], dtype=float)
    
    logger.info(f"[{sym}] Computing derived factors from {len(dates)} FUT_CLOSE rows ({dates[0]} ~ {dates[-1]})")
    
    # 计算派生因子
    returns_1d = np.full(len(closes), np.nan)
    returns_5d = np.full(len(closes), np.nan)
    vol_20d = np.full(len(closes), np.nan)
    high_20d = np.full(len(closes), np.nan)
    low_20d = np.full(len(closes), np.nan)
    
    for i in range(1, len(closes)):
        returns_1d[i] = (closes[i] / closes[i-1]) - 1.0
    
    for i in range(5, len(closes)):
        returns_5d[i] = (closes[i] / closes[i-5]) - 1.0
    
    for i in range(20, len(closes)):
        vol_20d[i] = np.std(returns_1d[i-19:i+1])
        high_20d[i] = np.max(closes[i-19:i+1])
        low_20d[i] = np.min(closes[i-19:i+1])
    
    factors = {
        f"{sym}_FUT_RETURN_1D": returns_1d,
        f"{sym}_FUT_RETURN_5D": returns_5d,
        f"{sym}_FUT_VOL_20D": vol_20d,
        f"{sym}_FUT_HIGH_20D": high_20d,
        f"{sym}_FUT_LOW_20D": low_20d,
    }
    
    for fname, values in factors.items():
        count = 0
        for i in range(len(dates)):
            if not np.isnan(values[i]):
                # PIT: skip obs_date == pub_date
                if dates[i] != PUB_DATE:
                    cur.execute("""
                        INSERT OR REPLACE INTO pit_factor_observations
                        (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (fname, sym, PUB_DATE, dates[i], float(values[i]), SOURCE, CONFIDENCE))
                    count += 1
        written += count
        logger.info(f"  {fname}: {count} records")
    
    conn.commit()
    logger.info(f"[{sym}] Derived factors: {written} total records")
    return written


def main():
    logger.info("=" * 60)
    logger.info("EC/LC/LH/SC 派生因子计算")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    total = 0
    for sym in SYMBOLS:
        logger.info(f"\n--- {sym} ---")
        n = compute_derived_factors(sym, conn)
        total += n
    
    conn.close()
    logger.info(f"\nTotal: {total} derived factor records written")
    logger.info("DONE")


if __name__ == "__main__":
    main()
