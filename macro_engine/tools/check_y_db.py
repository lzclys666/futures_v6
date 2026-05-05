import sqlite3

db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("=== Tables in pit_data.db ===")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    cnt = cur.fetchone()[0]
    print(f"  {t}: {cnt} rows")

# Check for Y data in any table
print()
print("=== Searching for Y factor data ===")
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{t}] WHERE symbol='Y'")
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f"  {t}: {cnt} rows with symbol='Y'")
            # Get column info
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = [c[1] for c in cur.fetchall()]
            print(f"    Columns: {cols}")
            
            # Get summary
            if 'factor_code' in cols and 'obs_date' in cols:
                cur.execute(f"SELECT factor_code, MAX(obs_date), COUNT(*) FROM [{t}] WHERE symbol='Y' GROUP BY factor_code ORDER BY MAX(obs_date) DESC")
                rows = cur.fetchall()
                for r in rows:
                    print(f"    {r[0]}: last={r[1]}, count={r[2]}")
    except Exception:
        pass

conn.close()
