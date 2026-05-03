# -*- coding: utf-8 -*-
from config.paths import PIT_DB
import sqlite3
conn = sqlite3.connect(str(PIT_DB))
cur = conn.cursor()

# 鍒楀嚭鎵€鏈夎〃
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

# 妫€鏌ユ瘡涓〃鐨勭粨鏋?
for t in tables:
    cur.execute(f'PRAGMA table_info({t})')
    cols = [(r[1], r[2]) for r in cur.fetchall()]
    print(f'{t}: {cols}')
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  Row count: {cur.fetchone()[0]}')
    if t == 'factor_data':
        cur.execute(f'SELECT * FROM {t} LIMIT 3')
        rows = cur.fetchall()
        print(f'  Sample rows: {rows}')

conn.close()
