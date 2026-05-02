import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cur = conn.cursor()

cur.execute("SELECT factor_code, symbol, obs_date, raw_value, source FROM pit_factor_observations WHERE pub_date='2026-04-20' ORDER BY factor_code")
rows = cur.fetchall()
print('Today records:', len(rows))
for r in rows:
    print(' ', r)

conn.close()
