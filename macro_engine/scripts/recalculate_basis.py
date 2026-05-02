#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新计算基差数据 - 使用每日期货收盘价和现货价格
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def recalculate_basis():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有需要重新计算的记录
    cursor.execute("""
        SELECT pub_date, obs_date, trade_date, contract, futures_close, spot_price
        FROM jm_futures_basis 
        ORDER BY obs_date
    """)
    
    records = cursor.fetchall()
    print(f"[INFO] 需要重新计算 {len(records)} 条记录")
    
    updated = 0
    for pub_date, obs_date, trade_date, contract, futures_close, spot_price in records:
        if futures_close and spot_price:
            # 重新计算基差和基差率
            basis = futures_close - spot_price
            basis_rate = (basis / spot_price) * 100 if spot_price != 0 else 0
            
            cursor.execute("""
                UPDATE jm_futures_basis 
                SET basis = ?, basis_rate = ?
                WHERE pub_date = ? AND obs_date = ? AND contract = ?
            """, (basis, basis_rate, pub_date, obs_date, contract))
            
            updated += 1
            
            if updated % 50 == 0:
                print(f"[PROGRESS] 已更新 {updated}/{len(records)}")
    
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(DISTINCT basis) FROM jm_futures_basis")
    unique_basis = cursor.fetchone()[0]
    print(f"[INFO] 不同的basis值数量: {unique_basis}")
    
    cursor.execute("SELECT COUNT(DISTINCT basis_rate) FROM jm_futures_basis")
    unique_rate = cursor.fetchone()[0]
    print(f"[INFO] 不同的basis_rate值数量: {unique_rate}")
    
    conn.close()
    
    print(f"[OK] 重新计算完成: {updated} 条记录")

if __name__ == "__main__":
    recalculate_basis()
