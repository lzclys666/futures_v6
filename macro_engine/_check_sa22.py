import sqlite3
db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 昨天(2026-04-22) SA数据
cur.execute('''
    SELECT factor_code, raw_value, source_confidence, source
    FROM pit_factor_observations
    WHERE symbol='SA' AND obs_date = '2026-04-22'
    ORDER BY factor_code
''')
rows = cur.fetchall()
print(f'SA 2026-04-22 记录数: {len(rows)}')
for r in rows:
    print(f'  {r[0]:<40} val={str(r[1]):<12} conf={r[2]} src={r[3]}')

# 对比今天和昨天的记录差异
print()
cur.execute('''
    SELECT factor_code FROM pit_factor_observations
    WHERE symbol='SA' AND obs_date = '2026-04-22'
''')
yesterday = set(r[0] for r in cur.fetchall())
cur.execute('''
    SELECT factor_code FROM pit_factor_observations
    WHERE symbol='SA' AND obs_date = '2026-04-23'
''')
today = set(r[0] for r in cur.fetchall())
print(f'昨天有今天无: {yesterday - today}')
print(f'今天有昨天无: {today - yesterday}')
conn.close()
