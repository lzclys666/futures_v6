import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Database tables:')
for t in tables:
    print(f'  {t[0]}')

conn.close()
