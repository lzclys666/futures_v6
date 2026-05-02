import sqlite3
db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# SA因子近3天记录
cur.execute('''
    SELECT factor_code, raw_value, obs_date, source_confidence, source
    FROM pit_factor_observations
    WHERE symbol='SA' AND obs_date >= '2026-04-21'
    ORDER BY factor_code, obs_date DESC
''')
rows = cur.fetchall()
print('SA因子近3天记录:')
for r in rows:
    print(f'  {r[0]:<35} val={r[1]} obs={r[2]} conf={r[3]} src={r[4]}')

# 也检查是否有今天的SA记录
cur.execute('''
    SELECT COUNT(DISTINCT factor_code) FROM pit_factor_observations
    WHERE symbol='SA' AND obs_date = '2026-04-23'
''')
today_count = cur.fetchone()[0]
print(f'\nSA 2026-04-23 记录数: {today_count}')

conn.close()
