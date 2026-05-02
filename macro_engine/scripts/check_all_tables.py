#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库表结构
"""
import sqlite3
from pathlib import Path

DB_PATH = Path('D:/futures_v6/macro_engine/pit_data.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 检查各品种的基差表
tables = ['ru_futures_basis', 'rb_futures_basis', 'zn_futures_basis', 'ni_futures_basis']
for table in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'{table}: {count} 条记录')
    except sqlite3.OperationalError as e:
        print(f'{table}: 表不存在 - {e}')

# 检查持仓量表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%hold_volume%'")
print('\n持仓量表:')
for row in cursor.fetchall():
    print(f'  {row[0]}')

# 检查波动率表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%volatility%'")
print('\n波动率表:')
for row in cursor.fetchall():
    print(f'  {row[0]}')

# 检查进口表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%import%'")
print('\n进口表:')
for row in cursor.fetchall():
    print(f'  {row[0]}')

conn.close()
