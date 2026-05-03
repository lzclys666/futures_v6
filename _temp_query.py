from config.paths import PIT_DB
import sqlite3
conn = sqlite3.connect(str(PIT_DB))
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
for t in tables:
    c.execute(f"SELECT * FROM {t} LIMIT 3")
    print(f"\n{t} columns:", [d[0] for d in c.description])
    print(f"{t} rows:", c.fetchall())
conn.close()
