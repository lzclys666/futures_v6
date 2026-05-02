"""检查 JM spread PIT 状态"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 1. 检查 JM 相关表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%jm%'")
print('JM相关表:', cur.fetchall())

# 2. 当前违规数量
cur.execute('''
SELECT COUNT(*) FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%')
AND obs_date IS NOT NULL AND pub_date > obs_date
''')
violations = cur.fetchone()[0]
print(f'JM违规记录数: {violations}')

# 3. 查看违规记录样本
cur.execute('''
SELECT symbol, pub_date, obs_date, close 
FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%')
AND pub_date > obs_date
LIMIT 5
''')
print('违规样本:')
for row in cur.fetchall():
    print(f'  {row}')

# 4. 检查 trade_date 字段
cur.execute('''
SELECT obs_date, pub_date, trade_date, close 
FROM pit_factor_observations 
WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%') AND trade_date IS NOT NULL
LIMIT 5
''')
print('trade_date样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, pub={row[1]}, trade={row[2]}, close={row[3]}')

conn.close()
