#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复基差波动率数据 - 基于基差历史计算波动率
"""
import sqlite3
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def fix_volatility_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(jm_basis_volatility)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"[INFO] jm_basis_volatility 列: {columns}")
    
    # 获取基差数据
    cursor.execute("""
        SELECT obs_date, basis FROM jm_futures_basis 
        WHERE basis IS NOT NULL
        ORDER BY obs_date
    """)
    
    basis_data = cursor.fetchall()
    print(f"[INFO] 基差数据条数: {len(basis_data)}")
    
    if len(basis_data) < 20:
        print("[WARN] 基差数据不足，无法计算波动率")
        return
    
    # 计算滚动波动率（20日）
    basis_values = [row[1] for row in basis_data]
    dates = [row[0] for row in basis_data]
    
    window = 20
    fixed = 0
    
    for i in range(window, len(basis_values)):
        window_values = basis_values[i-window:i]
        basis_vol_20d = np.std(window_values)
        basis_vol_10d = np.std(basis_values[i-10:i]) if i >= 10 else None
        basis_vol_5d = np.std(basis_values[i-5:i]) if i >= 5 else None
        
        obs_date = dates[i]
        pub_date = dates[i]  # 使用相同日期
        
        # 检查是否已存在
        cursor.execute("""
            SELECT COUNT(*) FROM jm_basis_volatility WHERE obs_date = ?
        """, (obs_date,))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO jm_basis_volatility (pub_date, obs_date, trade_date, basis_vol_5d, basis_vol_10d, basis_vol_20d)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pub_date, obs_date, obs_date, basis_vol_5d, basis_vol_10d, basis_vol_20d))
        else:
            cursor.execute("""
                UPDATE jm_basis_volatility 
                SET basis_vol_5d = ?, basis_vol_10d = ?, basis_vol_20d = ?
                WHERE obs_date = ?
            """, (basis_vol_5d, basis_vol_10d, basis_vol_20d, obs_date))
        
        fixed += 1
    
    conn.commit()
    conn.close()
    
    print(f"[OK] 修复完成: {fixed} 条记录")

if __name__ == "__main__":
    fix_volatility_data()
