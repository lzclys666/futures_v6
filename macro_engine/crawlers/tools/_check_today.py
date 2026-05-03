# -*- coding: utf-8 -*-
"""检查今日采集结果"""
import sqlite3
db = r'D:\futures_v6\macro_engine\crawlers\common\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 查所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

# 查今日更新的因子
import datetime
today = datetime.date.today().isoformat()
yesterday = datetime.date.today()
from datetime import timedelta
yesterday = (datetime.date.today() - timedelta(days=1)).isoformat()

cur.execute(f"""
SELECT factor_code, symbol, raw_value, obs_date, pub_date, source_confidence
FROM factors
WHERE pub_date >= '{yesterday}'
ORDER BY obs_date DESC, factor_code
LIMIT 50
""")
rows = cur.fetchall()
print(f'\n昨日至今更新的因子 ({yesterday} ~ {today}):')
for r in rows:
    print(f'  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]}, conf={r[5]})')

conn.close()
