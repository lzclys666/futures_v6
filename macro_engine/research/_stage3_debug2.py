"""Debug _load_factor_from_pit"""
import sqlite3
import pandas as pd

DB_PATH = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB_PATH)

factor_code = 'CU_AL_ratio'
symbol = 'CU'
lookback = 500

df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code=? AND symbol=? "
    "ORDER BY obs_date DESC LIMIT ?",
    conn, params=(factor_code, symbol, lookback)
)
print('SQL返回行数:', len(df))
print('列名:', list(df.columns))
print(df.head(3))

df['date'] = pd.to_datetime(df['obs_date'])
print('to_datetime后:', len(df))
df2 = df.drop_duplicates('date', keep='first')
print('drop_duplicates后:', len(df2))
df2.set_index('date', inplace=True)
print('set_index后:', len(df2))
df2 = df2.sort_index()
print('sort_index后:', len(df2))
print('Index范围:', df2.index[0], '~', df2.index[-1])

conn.close()
