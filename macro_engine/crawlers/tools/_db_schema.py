# -*- coding: utf-8 -*-
"""检查数据库schema"""
import sqlite3
db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)

if tables:
    # 看第一个表的schema
    cur.execute(f"PRAGMA table_info('{tables[0][0]}')")
    print('Schema:', cur.fetchall())

conn.close()
