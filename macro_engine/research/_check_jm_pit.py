import sqlite3, pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

tables = [
    'jm_futures_ohlcv',
    'jm_futures_spread',
    'jm_futures_hold_volume',
    'jm_basis_volatility',
    'jm_import_monthly',
    'jm_futures_basis'
]

print("=== JM 所有表 obs_date vs trade_date 对比 ===\n")
for tbl in tables:
    try:
        df = pd.read_sql(f"SELECT * FROM {tbl} ORDER BY obs_date DESC, trade_date DESC LIMIT 8", conn)
        print(f"--- {tbl} ---")
        # Show date columns
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        print(df[date_cols].to_string())
        print()
    except Exception as e:
        print(f"  Error: {e}\n")

conn.close()
