import sqlite3
for db_path in [
    'D:/futures_v6/macro_engine/data/pit_factors.db',
    'D:/futures_v6/macro_engine/data/macro_factors.db',
    'D:/futures_v6/macro_engine/data/futures_data.db',
    'D:/futures_v6/pit_data.db',
]:
    print(f"\n=== {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print("Tables:", tables)
        for t in tables[:5]:
            c.execute(f"SELECT * FROM {t} LIMIT 2")
            cols = [d[0] for d in c.description]
            print(f"  {t}: {cols}")
            rows = c.fetchall()
            print(f"  sample: {rows[:2]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
