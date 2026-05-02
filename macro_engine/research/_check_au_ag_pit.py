"""检查 AG/AU 在 PIT 的 factor_code"""
import sqlite3, pandas as pd

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)

for sym in ['AG', 'AU']:
    rows = pd.read_sql(
        "SELECT factor_code, symbol, COUNT(*) as cnt, "
        "MIN(obs_date) as earliest, MAX(obs_date) as latest "
        "FROM pit_factor_observations WHERE symbol=? "
        "GROUP BY factor_code, symbol ORDER BY cnt DESC",
        conn, params=(sym,))
    print(f"\n=== {sym} ===")
    print(rows.to_string())

conn.close()
