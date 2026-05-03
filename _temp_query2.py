from config.paths import MACRO_ENGINE
import sqlite3
conn = sqlite3.connect('str(MACRO_ENGINE)/data/pit_factors.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
for t in tables:
    try:
        c.execute(f"SELECT * FROM {t} LIMIT 3")
        print(f"\n{t} columns:", [d[0] for d in c.description])
        rows = c.fetchall()
        print(f"{t} sample rows:", rows)
    except Exception as e:
        print(f"{t} error: {e}")
conn.close()
