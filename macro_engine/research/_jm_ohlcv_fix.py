"""执行 jm_futures_ohlcv PIT 修复：用 trade_date 覆盖错误的 obs_date"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 修复前
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date != trade_date")
before = cur.fetchone()[0]
print(f'修复前 obs_date != trade_date: {before}')

# 执行修复
cur.execute('''
UPDATE jm_futures_ohlcv
SET obs_date = trade_date
WHERE obs_date != trade_date AND trade_date IS NOT NULL
''')
conn.commit()
affected = cur.rowcount
print(f'UPDATE影响行数: {affected}')

# 修复后
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date != trade_date")
after = cur.fetchone()[0]
print(f'修复后 obs_date != trade_date: {after}')

# 验证样本
cur.execute("SELECT obs_date, trade_date, pub_date, open, close FROM jm_futures_ohlcv LIMIT 5")
print('\n修复后样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, trade={row[1]}, pub={row[2]}, O={row[3]}, C={row[4]}')

conn.close()
print(f'\nPIT修复完成: {before} -> {after} 条未对齐')
