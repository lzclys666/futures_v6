# -*- coding: utf-8 -*-
"""检查数据库和今日采集结果"""
import sqlite3, datetime
db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 查所有因子今日更新情况
today = datetime.date.today().isoformat()
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

# 查今日更新的因子
cur.execute(f"""
SELECT factor_code, symbol, raw_value, obs_date, pub_date, source_confidence
FROM factors
WHERE pub_date >= '{yesterday}'
ORDER BY factor_code
LIMIT 100
""")
rows = cur.fetchall()
print(f'=== 昨日至今 ({yesterday} ~ {today}) 更新的因子 ===')
print(f'共 {len(rows)} 条')
for r in rows:
    print(f'  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]}, conf={r[5]})')

# 查各品种因子数量
cur.execute("""
SELECT symbol, COUNT(*) as cnt 
FROM factors 
WHERE obs_date >= date('now', '-7 days')
GROUP BY symbol 
ORDER BY cnt DESC
""")
print(f'\n=== 近7天各品种因子数量 ===')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]} 个因子')

conn.close()
