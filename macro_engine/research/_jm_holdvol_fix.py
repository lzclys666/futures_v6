"""修复 jm_futures_hold_volume PIT"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM jm_futures_hold_volume WHERE obs_date != trade_date")
before = cur.fetchone()[0]
print(f'修复前 obs_date != trade_date: {before}')

cur.execute('''
UPDATE jm_futures_hold_volume
SET obs_date = trade_date
WHERE obs_date != trade_date AND trade_date IS NOT NULL
''')
conn.commit()
affected = cur.rowcount
print(f'UPDATE影响: {affected}')

cur.execute("SELECT COUNT(*) FROM jm_futures_hold_volume WHERE obs_date != trade_date")
after = cur.fetchone()[0]
print(f'修复后: {after}')

# 验证样本
cur.execute("SELECT obs_date, trade_date, pub_date, hold_volume FROM jm_futures_hold_volume LIMIT 3")
for row in cur.fetchall():
    print(f'  obs={row[0]}, trade={row[1]}, pub={row[2]}, vol={row[3]}')

conn.close()
print(f'\n修复完成: {before} -> {after}')
