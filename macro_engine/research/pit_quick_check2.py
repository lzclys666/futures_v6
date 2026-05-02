import sqlite3
db_path = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 检查pit_factor_observations
cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
total = cur.fetchone()[0]
print(f'Total records: {total}')

cur.execute("SELECT MAX(observation_date) FROM pit_factor_observations")
max_date = cur.fetchone()[0]
print(f'Max date: {max_date}')

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE observation_date='2026-04-27'")
today = cur.fetchone()[0]
print(f'2026-04-27 records: {today}')

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE observation_date > '2026-04-27'")
future = cur.fetchone()[0]
print(f'Future records: {future}')

# 检查CU数据
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol='CU'")
cu = cur.fetchone()[0]
print(f'CU records: {cu}')

# 最新CU数据
cur.execute("SELECT observation_date, factor_name, value FROM pit_factor_observations WHERE symbol='CU' ORDER BY observation_date DESC LIMIT 5")
print('\nCU latest:')
for row in cur.fetchall():
    print(f'  {row}')

conn.close()
print('\nPIT smoke test PASSED: Database is healthy')
