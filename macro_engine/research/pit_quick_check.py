import sqlite3
db_path = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f'Tables: {tables}')
cur.execute("SELECT COUNT(*) FROM factor_data WHERE symbol='CU'")
print(f'CU records: {cur.fetchone()[0]}')
cur.execute("SELECT MAX(date) FROM factor_data")
print(f'Max date: {cur.fetchone()[0]}')
cur.execute("SELECT COUNT(*) FROM factor_data WHERE date='2026-04-27'")
print(f'2026-04-27 records: {cur.fetchone()[0]}')
cur.execute("SELECT COUNT(*) FROM factor_data WHERE date > '2026-04-27'")
print(f'Future records (>2026-04-27): {cur.fetchone()[0]}')
conn.close()
