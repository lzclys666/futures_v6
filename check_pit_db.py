from config.paths import MACRO_ENGINE
import sqlite3

db = 'str(MACRO_ENGINE)/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 查看所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])

# 检查 pit_factor_observations 数据量
cur.execute('SELECT COUNT(*) FROM pit_factor_observations')
print('Factor obs count:', cur.fetchone()[0])

# 找价格相关表
price_tables = [t for t in tables if any(k in t[0].lower() for k in ['bar', 'price', 'daily', 'return'])]
print('Price-related tables:', price_tables)

# 检查因子数据最近日期
cur.execute("SELECT symbol, factor_code, MAX(obs_date) FROM pit_factor_observations GROUP BY symbol, factor_code LIMIT 5")
print('Latest factor dates:')
for row in cur.fetchall():
    print(f'  {row}')

# 检查 bar_data 表
if any('bar' in t[0].lower() for t in tables):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%bar%'")
    print('Bar tables:', cur.fetchall())

conn.close()
