"""Check CU_AL_ratio PIT violation pattern"""
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

df = pd.read_sql(
    "SELECT obs_date, pub_date FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' ORDER BY obs_date",
    conn
)
print(f"Total CU_AL_ratio records: {len(df)}")
print(f"First: obs={df.iloc[0]['obs_date']} pub={df.iloc[0]['pub_date']}")
print(f"Last:  obs={df.iloc[-1]['obs_date']} pub={df.iloc[-1]['pub_date']}")
print(f"All pub_date == obs_date: {(df['pub_date'] == df['obs_date']).all()}")

# Also check what a correct factor looks like
df2 = pd.read_sql(
    "SELECT factor_code, symbol, obs_date, pub_date FROM pit_factor_observations "
    "WHERE factor_code='AG_MACRO_GOLD_SILVER_RATIO' ORDER BY obs_date DESC LIMIT 5",
    conn
)
print("\nAG_MACRO_GOLD_SILVER_RATIO (correct pattern):")
for _, row in df2.iterrows():
    print(f"  obs={row['obs_date']} pub={row['pub_date']}")

conn.close()
