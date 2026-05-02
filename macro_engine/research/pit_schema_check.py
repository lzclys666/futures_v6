import sqlite3
db_path = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(pit_factor_observations)")
print("pit_factor_observations columns:")
for row in cur.fetchall():
    print(f"  {row}")

cur.execute("SELECT * FROM pit_factor_observations LIMIT 3")
rows = cur.fetchall()
if rows:
    print("\nSample data:")
    for row in rows:
        print(f"  {row}")
else:
    print("\nTable is empty")

conn.close()
