#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""
重新生成其他品种的模拟因子数据（修正版）
"""
import sqlite3
import numpy as np
from pathlib import Path

DB_PATH = Path('str(MACRO_ENGINE)/pit_data.db')

SYMBOLS = ['RU', 'RB', 'ZN', 'NI']


def create_table_if_not_exists(cursor, table_name, template_table):
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM {template_table} WHERE 1=0"
    cursor.execute(sql)


def rebuild_mock_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for symbol in SYMBOLS:
        sym = symbol.lower()
        print(f"\n=== {symbol} ===")
        
        # 获取 OHLCV
        cursor.execute(f"""
            SELECT obs_date, close, volume 
            FROM jm_futures_ohlcv 
            WHERE contract = '{symbol}0'
            ORDER BY obs_date
        """)
        rows = cursor.fetchall()
        if not rows:
            print(f"  无数据")
            continue
        
        dates = [r[0] for r in rows]
        closes = [r[1] for r in rows]
        volumes = [r[2] or 0 for r in rows]
        n = len(dates)
        last_date = dates[-1]

        rng = np.random.RandomState(abs(hash(symbol)) % (2**31))
        
        # === 1. 基差表 ===
        cursor.execute(f"DROP TABLE IF EXISTS {sym}_futures_basis")
        create_table_if_not_exists(cursor, f"{sym}_futures_basis", "jm_futures_basis")
        
        spot_base = np.mean(closes) * 0.95
        spot = spot_base + rng.randn(n) * spot_base * 0.02
        basis = np.array(closes) - spot
        basis_rate = (basis / spot) * 100
        
        for i in range(n):
            cursor.execute(f"INSERT INTO {sym}_futures_basis (pub_date, obs_date, trade_date, contract, futures_settle, futures_close, spot_price, spot_source, basis, basis_rate, data_status) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                last_date, dates[i], dates[i], f'{symbol}2505',
                round(closes[i], 1), round(closes[i], 1),
                round(float(spot[i]), 1), 'simulated',
                round(float(basis[i]), 1), round(float(basis_rate[i]), 2),
                'simulated'
            ))
        print(f"  basis: {n} 条")
        
        # === 2. 仓量表 === (不用contract filter，用groupby聚合)
        cursor.execute(f"DROP TABLE IF EXISTS {sym}_futures_hold_volume")
        create_table_if_not_exists(cursor, f"{sym}_futures_hold_volume", "jm_futures_hold_volume")
        
        mean_vol = max(np.mean(volumes), 1000)
        hold = np.maximum(100, mean_vol + rng.randn(n) * mean_vol * 0.3)
        hold_change = np.diff(hold, prepend=hold[0])
        
        for i in range(n):
            cursor.execute(f"INSERT INTO {sym}_futures_hold_volume (pub_date, obs_date, contract, trade_date, hold_volume, hold_change, volume) VALUES (?,?,?,?,?,?,?)", (
                last_date, dates[i], f'{symbol}0', dates[i],
                int(hold[i]), int(hold_change[i]), int(volumes[i])
            ))
        print(f"  hold_volume: {n} 条 (contract={symbol}0)")
        
        # === 3. 波动率表 ===
        cursor.execute(f"DROP TABLE IF EXISTS {sym}_basis_volatility")
        create_table_if_not_exists(cursor, f"{sym}_basis_volatility", "jm_basis_volatility")
        
        rets = np.diff(closes) / np.array(closes[:-1])
        for i in range(n):
            v5 = float(np.std(rets[max(0,i-4):i])) if i >= 5 else abs(closes[i] * 0.01)
            v10 = float(np.std(rets[max(0,i-9):i])) if i >= 10 else abs(closes[i] * 0.015)
            v20 = float(np.std(rets[max(0,i-19):i])) if i >= 20 else abs(closes[i] * 0.02)
            cursor.execute(f"INSERT INTO {sym}_basis_volatility (pub_date, obs_date, trade_date, basis_vol_5d, basis_vol_10d, basis_vol_20d) VALUES (?,?,?,?,?,?)", (
                last_date, dates[i], dates[i], round(v5, 6), round(v10, 6), round(v20, 6)
            ))
        print(f"  basis_volatility: {n} 条")
        
        # === 4. 进口表 === (月频，用每月1号作为obs_date)
        cursor.execute(f"DROP TABLE IF EXISTS {sym}_import_monthly")
        create_table_if_not_exists(cursor, f"{sym}_import_monthly", "jm_import_monthly")
        
        imp_vol = np.maximum(10, rng.randn(24) * 50 + 200)
        for m in range(24):
            month_str = f"2024-{(m+3)//12+1:02d}-{(m%12)+1:02d}-01"
            cursor.execute(f"INSERT INTO {sym}_import_monthly (pub_date, obs_date, import_volume, import_value, import_price, data_source, note) VALUES (?,?,?,?,?,?,?)", (
                last_date, month_str, round(float(imp_vol[m]), 1),
                round(float(imp_vol[m] * 150), 1), 150.0,
                'simulated', 'mock data'
            ))
        print(f"  import: 24 条 (月频)")
        
        # === 5. Spread 表 === (直接复制jm_futures_spread)
        cursor.execute(f"DROP TABLE IF EXISTS {sym}_futures_spread")
        create_table_if_not_exists(cursor, f"{sym}_futures_spread", "jm_futures_spread")
        cursor.execute(f"INSERT INTO {sym}_futures_spread SELECT * FROM jm_futures_spread")
        print(f"  spread: 复制自 jm_futures_spread")
    
    conn.commit()
    conn.close()
    print("\n[DONE] 所有模拟数据重新生成完成")


if __name__ == "__main__":
    rebuild_mock_data()
