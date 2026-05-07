import sqlite3
c = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ohlcv%'").fetchall()
print("OHLCV tables:", tables)

# Also check what factors exist for SN, M, Y
for sym in ['SN', 'M', 'Y']:
    rows = c.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol=?", (sym,)).fetchall()
    factors = [r[0] for r in rows]
    print(f"\n{sym} ({len(factors)} factors): {factors}")
c.close()
