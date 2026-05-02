"""最终确认所有JM表PIT状态"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'jm_%'")
tables = [r[0] for r in cur.fetchall()]
print('JM表PIT最终状态:')
for tbl in tables:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    prag = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})")]
    if 'trade_date' in prag:
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date")
        bad = cur.fetchone()[0]
        status = 'OK' if bad == 0 else f'BAD({bad})'
        print(f'  {tbl}: {total}条, obs_date!=trade_date: {bad} [{status}]')
    else:
        print(f'  {tbl}: {total}条, 无trade_date列 [跳过]')
conn.close()
