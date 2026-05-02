import sqlite3
db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 检查今天各品种是否有记录（用于判断cron是否运行）
today = '2026-04-23'
cur.execute('''
    SELECT symbol, COUNT(DISTINCT factor_code) as cnt, MAX(obs_date) as last_obs
    FROM pit_factor_observations
    WHERE obs_date = ?
    GROUP BY symbol
    ORDER BY cnt DESC
''', (today,))

rows = cur.fetchall()
print(f'各品种 2026-04-23 记录数:')
total_today = 0
for r in rows:
    print(f'  {r[0]:<6}: {r[1]:>4}因子  last_obs={r[2]}')
    total_today += r[1]

print(f'\n今日共 {len(rows)} 个品种有数据，{total_today} 条记录')

# 检查哪些品种今天没有数据
all_symbols = ['AG','AL','AO','AU','BR','BU','CU','EC','EG','HC','I','J','JM','LC','LH','M','NR','P','PB','PP','RB','RU','SA','SC','SN','TA','Y','ZN']
today_symbols = set(r[0] for r in rows)
missing = [s for s in all_symbols if s not in today_symbols]
print(f'今日缺数据品种: {missing}')

conn.close()
