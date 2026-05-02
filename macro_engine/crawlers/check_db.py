import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cur = conn.cursor()

# 列出所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

# 检查每个表的结构
for t in tables:
    cur.execute(f'PRAGMA table_info({t})')
    cols = [(r[1], r[2]) for r in cur.fetchall()]
    print(f'{t}: {cols}')
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  Row count: {cur.fetchone()[0]}')
    if t == 'factor_data':
        cur.execute(f'SELECT * FROM {t} LIMIT 3')
        rows = cur.fetchall()
        print(f'  Sample rows: {rows}')

conn.close()
