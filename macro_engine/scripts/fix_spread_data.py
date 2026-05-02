#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复价差数据 - 计算主力合约和次主力合约的价差
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pit_data.db"

def fix_spread_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(jm_futures_spread)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"[INFO] jm_futures_spread 列: {columns}")
    
    # 检查有多少条记录需要修复
    cursor.execute("""
        SELECT COUNT(*) FROM jm_futures_spread 
        WHERE spread_01 IS NULL
    """)
    total_to_fix = cursor.fetchone()[0]
    print(f"[INFO] 需要修复的记录数: {total_to_fix}")
    
    if total_to_fix == 0:
        print("[INFO] 无需修复")
        return
    
    # 获取所有需要修复的记录
    cursor.execute("""
        SELECT pub_date, obs_date, trade_date
        FROM jm_futures_spread 
        WHERE spread_01 IS NULL
        ORDER BY obs_date
    """)
    
    records = cursor.fetchall()
    fixed = 0
    
    for pub_date, obs_date, trade_date in records:
        # 从 ohlcv 表获取不同合约的价格
        # 使用主力合约(JM0)和次主力合约(JM01)的价差
        cursor.execute("""
            SELECT contract, close FROM jm_futures_ohlcv 
            WHERE obs_date = ? AND contract LIKE 'JM%'
            ORDER BY contract
        """, (obs_date,))
        
        prices = {}
        for row in cursor.fetchall():
            contract, close = row
            if close:
                prices[contract] = close
        
        # 计算价差
        if len(prices) >= 2:
            contracts = sorted(prices.keys())
            price_0 = prices.get(contracts[0])  # 主力
            price_1 = prices.get(contracts[1]) if len(contracts) > 1 else None  # 次主力
            price_2 = prices.get(contracts[2]) if len(contracts) > 2 else None  # 第三
            
            spread_01 = price_0 - price_1 if price_0 and price_1 else None
            spread_03 = price_0 - price_2 if price_0 and price_2 else None
            spread_05 = price_1 - price_2 if price_1 and price_2 else None
            
            cursor.execute("""
                UPDATE jm_futures_spread 
                SET spread_01 = ?, spread_03 = ?, spread_05 = ?
                WHERE pub_date = ? AND obs_date = ?
            """, (spread_01, spread_03, spread_05, pub_date, obs_date))
            
            fixed += 1
            
            if fixed % 50 == 0:
                print(f"[PROGRESS] 已修复 {fixed}/{total_to_fix}")
    
    conn.commit()
    conn.close()
    
    print(f"[OK] 修复完成: {fixed} 条记录")

if __name__ == "__main__":
    fix_spread_data()
