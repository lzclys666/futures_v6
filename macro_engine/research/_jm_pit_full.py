"""完整检查 JM PIT 状态"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 1. pit_factor_observations 表结构
cur.execute("PRAGMA table_info(pit_factor_observations)")
print('pit_factor_observations 列:', [r[1] for r in cur.fetchall()])

# 2. jm_futures_spread 表结构
cur.execute("PRAGMA table_info(jm_futures_spread)")
print('jm_futures_spread 列:', [r[1] for r in cur.fetchall()])

# 3. pit_factor_observations 中 JM 相关记录
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol LIKE '%JM%' OR symbol LIKE '%jm%'")
print(f'pit_factor_observations JM记录: {cur.fetchone()[0]}')

# 4. pit_factor_observations JM 违规
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE (symbol LIKE '%JM%' OR symbol LIKE '%jm%') AND obs_date IS NOT NULL AND pub_date > obs_date")
print(f'pit_factor_observations JM违规: {cur.fetchone()[0]}')

# 5. jm_futures_spread 记录数
cur.execute("SELECT COUNT(*) FROM jm_futures_spread")
print(f'jm_futures_spread 总记录: {cur.fetchone()[0]}')

# 6. jm_futures_spread 违规
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE pub_date > obs_date")
print(f'jm_futures_spread 违规: {cur.fetchone()[0]}')

# 7. 查看 jm_futures_spread 样本
cur.execute("SELECT obs_date, pub_date, raw_value FROM jm_futures_spread LIMIT 5")
print('jm_futures_spread样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, pub={row[1]}, value={row[2]}')

# 8. 查看 jm_futures_spread 违规样本
cur.execute("SELECT obs_date, pub_date, raw_value FROM jm_futures_spread WHERE pub_date > obs_date LIMIT 5")
print('jm_futures_spread违规样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, pub={row[1]}, value={row[2]}')

conn.close()
