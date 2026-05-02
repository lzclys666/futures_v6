"""全库最终 PIT 验证"""
import sqlite3
DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall()]
total_v = 0
for tbl in all_tables:
    cur.execute(f"PRAGMA table_info({tbl})")
    cols = [r[1] for r in cur.fetchall()]
    if 'obs_date' in cols and 'trade_date' in cols:
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
        v = cur.fetchone()[0]
        if v > 0:
            print(f'VIOLATION: {tbl}: {v}')
            total_v += v
if total_v == 0:
    print('FULL DATABASE: 0 violations - ALL PASS')
conn.close()
