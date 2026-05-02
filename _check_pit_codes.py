import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations ORDER BY factor_code")
codes = [r[0] for r in cur.fetchall()]
conn.close()
# Filter relevant ones
for c in codes:
    if any(k in c.lower() for k in ['ratio', 'al', 'cu', 'usd', 'cny', 'cn10y', 'wti', 'brent', 'spread']):
        print(c)
print(f"\nTotal factor codes in PIT: {len(codes)}")
