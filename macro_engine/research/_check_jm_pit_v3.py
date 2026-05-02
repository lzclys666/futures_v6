"""检查 JM spread PIT 状态 v3"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 1. 表结构
cur.execute("PRAGMA table_info(pit_factor_observations)")
cols = [row[1] for row in cur.fetchall()]
print('pit_factor_observations 列:', cols)

# 2. 当前违规数量
cur.execute(f'''
SELECT COUNT(*) FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%')
AND obs_date IS NOT NULL AND pub_date > obs_date
''')
violations = cur.fetchone()[0]
print(f'JM违规记录数: {violations}')

# 3. 查看违规记录样本
cur.execute(f'''
SELECT symbol, pub_date, obs_date, trade_date 
FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%')
AND pub_date > obs_date
LIMIT 5
''')
print('违规样本:')
for row in cur.fetchall():
    print(f'  {row}')

# 4. trade_date 样本
cur.execute('''
SELECT obs_date, pub_date, trade_date 
FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%') AND trade_date IS NOT NULL
LIMIT 5
''')
print('trade_date样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, pub={row[1]}, trade={row[2]}')

# 5. jm_futures_spread 总记录数
cur.execute("SELECT COUNT(*) FROM jm_futures_spread")
total = cur.fetchone()[0]
print(f'jm_futures_spread 总记录: {total}')

# 6. jm_futures_spread 的 obs_date vs pub_date 情况
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE pub_date > obs_date")
spread_violations = cur.fetchone()[0]
print(f'jm_futures_spread pub_date>obs_date: {spread_violations}')

# 7. spread 表结构
cur.execute("PRAGMA table_info(jm_futures_spread)")
spread_cols = [row[1] for row in cur.fetchall()]
print('jm_futures_spread 列:', spread_cols)

conn.close()
