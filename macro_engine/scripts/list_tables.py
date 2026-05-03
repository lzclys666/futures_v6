from config.paths import MACRO_ENGINE
import sqlite3
conn = sqlite3.connect('str(MACRO_ENGINE)/pit_data.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Database tables:')
for t in tables:
    print(f'  {t[0]}')

conn.close()
