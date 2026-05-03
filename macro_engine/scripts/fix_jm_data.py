#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""修复 JM 的 hold_volume 数据：obs_date = trade_date"""
import sqlite3
from pathlib import Path

DB_PATH = Path('str(MACRO_ENGINE)/pit_data.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Fix JM hold_volume
cursor.execute("UPDATE jm_futures_hold_volume SET obs_date = trade_date WHERE obs_date != trade_date")
print(f"JM hold_volume: 修复 {cursor.rowcount} 条 obs_date")

cursor.execute("SELECT COUNT(DISTINCT obs_date) FROM jm_futures_hold_volume WHERE contract LIKE 'JM%'")
print(f"JM hold_volume distinct obs_dates: {cursor.fetchone()[0]}")

# Fix JM basis_volatility
cursor.execute("UPDATE jm_basis_volatility SET obs_date = trade_date WHERE obs_date != trade_date")
print(f"JM basis_volatility: 修复 {cursor.rowcount} 条")

conn.commit()
conn.close()
print("[DONE]")
