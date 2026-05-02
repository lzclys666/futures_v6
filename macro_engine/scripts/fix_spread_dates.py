#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复价差表日期 - 将 trade_date 复制到 obs_date
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def fix_spread_dates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查当前状态
    cursor.execute("SELECT COUNT(DISTINCT obs_date) FROM jm_futures_spread")
    unique_obs = cursor.fetchone()[0]
    print(f"[INFO] 当前唯一 obs_date 数: {unique_obs}")
    
    # 将 trade_date 复制到 obs_date
    cursor.execute("""
        UPDATE jm_futures_spread 
        SET obs_date = trade_date
        WHERE obs_date != trade_date OR obs_date IS NULL
    """)
    
    updated = cursor.rowcount
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(DISTINCT obs_date) FROM jm_futures_spread")
    new_unique = cursor.fetchone()[0]
    print(f"[INFO] 更新后唯一 obs_date 数: {new_unique}")
    
    conn.close()
    
    print(f"[OK] 更新完成: {updated} 条记录")

if __name__ == "__main__":
    fix_spread_dates()
