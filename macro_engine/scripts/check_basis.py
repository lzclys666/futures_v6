import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cursor = conn.cursor()

# 检查 jm_futures_basis 表结构
cursor.execute("PRAGMA table_info(jm_futures_basis)")
columns = cursor.fetchall()
print('jm_futures_basis columns:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

# 查看前5条数据
cursor.execute("SELECT * FROM jm_futures_basis LIMIT 5")
rows = cursor.fetchall()
print('\nFirst 5 rows:')
for row in rows:
    print(f'  {row}')

conn.close()
