"""执行 JM spread PIT 修复：用 trade_date 覆盖 obs_date"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 修复前状态
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE pub_date > obs_date")
before = cur.fetchone()[0]
print(f'修复前违规: {before}')

# 执行修复：trade_date -> obs_date（只修复 pub_date > obs_date 的记录）
cur.execute('''
UPDATE jm_futures_spread 
SET obs_date = trade_date 
WHERE pub_date > obs_date AND trade_date IS NOT NULL
''')
conn.commit()
affected = cur.rowcount
print(f'UPDATE影响行数: {affected}')

# 修复后状态
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE pub_date > obs_date")
after = cur.fetchone()[0]
print(f'修复后违规: {after}')

# 样本验证
cur.execute("SELECT obs_date, pub_date, trade_date, spread_01 FROM jm_futures_spread LIMIT 5")
print('修复后样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, pub={row[1]}, trade={row[2]}, spread={row[3]}')

conn.close()
print(f'\nPIT修复完成: {before} -> {after} 违规')
