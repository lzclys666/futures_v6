#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复进口数据 - 生成模拟进口数据用于测试
实际生产环境应从海关或行业数据源获取
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def fix_import_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(jm_import_monthly)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"[INFO] jm_import_monthly 列: {columns}")
    
    # 获取日期范围
    cursor.execute("SELECT MIN(obs_date), MAX(obs_date) FROM jm_futures_basis")
    min_date, max_date = cursor.fetchone()
    
    if not min_date or not max_date:
        print("[WARN] 无基础数据，无法生成进口数据")
        return
    
    print(f"[INFO] 日期范围: {min_date} ~ {max_date}")
    
    # 生成月度进口数据（模拟数据）
    start_date = datetime.strptime(min_date, "%Y-%m-%d")
    end_date = datetime.strptime(max_date, "%Y-%m-%d")
    
    # 焦煤进口数据（万吨）- 基于历史均值生成
    base_import = 450  # 月均进口量基准
    fixed = 0
    
    current = start_date
    while current <= end_date:
        # 生成该月的进口数据（带季节性波动）
        month = current.month
        seasonal_factor = 1.0 + 0.2 * (1 if month in [1, 2, 11, 12] else -0.1 if month in [6, 7, 8] else 0)
        import_qty = base_import * seasonal_factor * (1 + random.uniform(-0.15, 0.15))
        import_qty_yoy = random.uniform(-20, 30)  # 同比变化
        
        obs_date = current.strftime("%Y-%m-%d")
        pub_date = obs_date
        
        # 检查是否已存在
        cursor.execute("""
            SELECT COUNT(*) FROM jm_import_monthly WHERE obs_date = ?
        """, (obs_date,))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO jm_import_monthly (pub_date, obs_date, import_volume, import_value, import_price, data_source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pub_date, obs_date, round(import_qty, 2), round(import_qty * 150, 2), 150, 'simulated'))
        else:
            cursor.execute("""
                UPDATE jm_import_monthly 
                SET import_volume = ?, import_value = ?, import_price = ?, data_source = 'simulated'
                WHERE obs_date = ?
            """, (round(import_qty, 2), round(import_qty * 150, 2), 150, obs_date))
        
        fixed += 1
        
        # 移动到下个月
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    conn.commit()
    conn.close()
    
    print(f"[OK] 修复完成: {fixed} 条记录")

if __name__ == "__main__":
    fix_import_data()
