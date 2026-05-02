"""验证 RollingICCalculator 对 CU_AL_ratio 的 IC"""
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import RollingICCalculator
import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# 加载 CU_AL_ratio (升序)
r_df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_AL_ratio' AND symbol='CU' ORDER BY obs_date",
    conn)
r_df['date'] = pd.to_datetime(r_df['obs_date'])
r_df = r_df.drop_duplicates('date', keep='first')
r_df.set_index('date', inplace=True)

# 加载 CU_FUT_CLOSE (升序)
p_df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_FUT_CLOSE' AND symbol='CU' ORDER BY obs_date",
    conn)
p_df['date'] = pd.to_datetime(p_df['obs_date'])
p_df = p_df.drop_duplicates('date', keep='first')
p_df.set_index('date', inplace=True)
conn.close()

# 合并
df = pd.DataFrame({'f': r_df['raw_value'], 'p': p_df['raw_value']})
df = df[~df.index.duplicated(keep='first')].dropna()
print('合并后: {} rows ({} ~ {})'.format(
    len(df), df.index[0].date(), df.index[-1].date()))

for HOLD in [10, 20]:
    fwd_ret = df['p'].pct_change(HOLD).shift(-HOLD)
    df_with_fwd = df.copy()
    df_with_fwd['fwd'] = fwd_ret
    df_valid = df_with_fwd[['f', 'fwd']].dropna()
    print('\nHOLD={}: 有效数据 {} rows ({} ~ {})'.format(
        HOLD, len(df_valid),
        df_valid.index[0].date(), df_valid.index[-1].date()))

    ric = RollingICCalculator(window=60)
    ic_series = ric.compute_rolling_ic(df_valid['f'], df_valid['fwd'])
    print('  IC series length: {}'.format(len(ic_series)))
    if len(ic_series) > 0:
        print('  IC mean={:.4f} std={:.4f}'.format(ic_series.mean(), ic_series.std()))
        print('  IC win_rate={:.1%}'.format((ic_series > 0).mean()))
        print('  IC last5: {}'.format([round(x, 4) for x in ic_series.tail(5).tolist()]))
        print('  IC head5: {}'.format([round(x, 4) for x in ic_series.head(5).tolist()]))
    else:
        print('  IC series empty!')
