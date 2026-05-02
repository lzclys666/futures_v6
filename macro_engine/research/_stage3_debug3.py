"""Debug price loading"""
import sqlite3
import pandas as pd

DB_PATH = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB_PATH)

# 查CU的价格数据
df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE symbol='CU' ORDER BY obs_date DESC LIMIT 20",
    conn
)
df['date'] = pd.to_datetime(df['obs_date'])
print('CU price (newest 20):')
print(df[['obs_date','raw_value']].to_string())

print()
# 查CU有多少条
total = conn.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol='CU'").fetchone()[0]
print('CU total observations:', total)

# 查CU的factor_code分布
dist = pd.read_sql(
    "SELECT factor_code, COUNT(*) as cnt FROM pit_factor_observations "
    "WHERE symbol='CU' GROUP BY factor_code ORDER BY cnt DESC LIMIT 10",
    conn
)
print('\nCU factor_code 分布:')
print(dist.to_string())

conn.close()
