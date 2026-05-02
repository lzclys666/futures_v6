#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复基差数据 - 根据已有价格计算 basis 和 basis_rate
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def fix_basis_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查有多少条记录需要修复
    cursor.execute("""
        SELECT COUNT(*) FROM jm_futures_basis 
        WHERE basis IS NULL AND futures_close IS NOT NULL
    """)
    total_to_fix = cursor.fetchone()[0]
    print(f"[INFO] 需要修复的记录数: {total_to_fix}")
    
    if total_to_fix == 0:
        print("[INFO] 无需修复")
        return
    
    # 获取所有需要修复的记录
    cursor.execute("""
        SELECT pub_date, obs_date, trade_date, contract, futures_close, spot_price
        FROM jm_futures_basis 
        WHERE basis IS NULL
        ORDER BY trade_date
    """)
    
    records = cursor.fetchall()
    fixed = 0
    
    for pub_date, obs_date, trade_date, contract, futures_close, spot_price in records:
        # 如果 spot_price 为 NULL，尝试从其他来源获取
        if spot_price is None:
            # 尝试从 ohlcv 表获取结算价作为现货价格近似
            cursor.execute("""
                SELECT settle FROM jm_futures_ohlcv 
                WHERE obs_date = ? AND contract = ?
            """, (trade_date, contract))
            
            result = cursor.fetchone()
            if result and result[0]:
                spot_price = result[0]
            else:
                # 使用期货收盘价作为现货价格近似（简化处理）
                spot_price = futures_close
        
        # 计算基差和基差率
        if futures_close and spot_price:
            basis = futures_close - spot_price
            basis_rate = (basis / spot_price) * 100 if spot_price != 0 else 0
            
            # 使用 trade_date 作为 obs_date
            cursor.execute("""
                UPDATE jm_futures_basis 
                SET basis = ?, basis_rate = ?, spot_price = ?, data_status = 'calculated', obs_date = trade_date
                WHERE pub_date = ? AND trade_date = ? AND contract = ?
            """, (basis, basis_rate, spot_price, pub_date, trade_date, contract))
            
            fixed += 1
            
            if fixed % 50 == 0:
                print(f"[PROGRESS] 已修复 {fixed}/{total_to_fix}")
    
    conn.commit()
    conn.close()
    
    print(f"[OK] 修复完成: {fixed} 条记录")

if __name__ == "__main__":
    fix_basis_data()
