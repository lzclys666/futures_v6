"""CU_FUT_CLOSE 数据质量检查"""
import sqlite3
import pandas as pd
import numpy as np

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)

# 1. 检查 CU_FUT_CLOSE 的重复日期情况
print("=" * 60)
print("1. CU_FUT_CLOSE 重复日期检查")
print("=" * 60)
df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_FUT_CLOSE' AND symbol='CU' ORDER BY obs_date",
    conn)
df['date'] = pd.to_datetime(df['obs_date'])
dupes = df[df.duplicated('date', keep=False)]
print(f"总行数: {len(df)}, 唯—日期: {df['date'].nunique()}, 重复日期行数: {len(dupes)}")
if len(dupes) > 0:
    print("\n重复日期详情:")
    print(dupes.sort_values('date').to_string())

# 2. 检查是否有不同 factor_code 的价格数据混入
print("\n" + "=" * 60)
print("2. 所有 CU 相关因子（可能混入的）")
print("=" * 60)
variants = pd.read_sql(
    "SELECT factor_code, COUNT(*) as cnt, "
    "MIN(obs_date) as earliest, MAX(obs_date) as latest "
    "FROM pit_factor_observations "
    "WHERE symbol='CU' GROUP BY factor_code ORDER BY cnt DESC",
    conn)
print(variants.to_string())

# 3. 正确的价格数据应该是怎样的
print("\n" + "=" * 60)
print("3. 用主力合约规则验证：akshare 沪铜收盘价应在 50000-90000 范围")
print("=" * 60)
valid_prices = df[(df['raw_value'] > 30000) & (df['raw_value'] < 150000)]
print(f"合理价格范围(30000-150000)行数: {len(valid_prices)} / {len(df)}")
if len(valid_prices) > 0:
    print(f"  最小值: {valid_prices['raw_value'].min()}")
    print(f"  最大值: {valid_prices['raw_value'].max()}")
    print(f"  均值: {valid_prices['raw_value'].mean():.1f}")

# 4. 对比：看重复日期行的 raw_value 是否相同
print("\n" + "=" * 60)
print("4. 重复日期的 raw_value 是否相同？")
print("=" * 60)
dup_grp = dupes.groupby('date')['raw_value'].agg(['count', 'nunique', 'mean'])
print(dup_grp.to_string())

# 5. drop_duplicates 后的数据量
print("\n" + "=" * 60)
print("5. drop_duplicates(keep='first') 后的有效数据")
print("=" * 60)
df_uniq = df.drop_duplicates('date', keep='first')
print(f"去重后: {len(df_uniq)} 行")
print(f"日期范围: {df_uniq['date'].min().date()} ~ {df_uniq['date'].max().date()}")

# 6. 和 CU_AL_ratio 重叠的时间范围
print("\n" + "=" * 60)
print("6. CU_AL_ratio 和 CU_FUT_CLOSE 去重后时间重叠")
print("=" * 60)
r_df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_AL_ratio' AND symbol='CU' ORDER BY obs_date",
    conn)
r_df['date'] = pd.to_datetime(r_df['obs_date'])
r_uniq = r_df.drop_duplicates('date', keep='first')
overlap = pd.merge(
    df_uniq[['date']], r_uniq[['date']],
    on='date', how='inner'
)
print(f"CU_AL_ratio 范围: {r_uniq['date'].min().date()} ~ {r_uniq['date'].max().date()}")
print(f"CU_FUT_CLOSE 去重后范围: {df_uniq['date'].min().date()} ~ {df_uniq['date'].max().date()}")
print(f"重叠行数: {len(overlap)}")

conn.close()
