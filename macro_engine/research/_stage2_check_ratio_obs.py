"""
Stage 2: 检查金银比和CU/AL CSV + PIT注册情况
"""
import sqlite3
import pandas as pd
import os

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# 1. 检查金银比是否已在PIT
print("=== 金银比 PIT 注册情况 ===")
q = "SELECT factor_code, factor_name, direction, frequency FROM factor_metadata WHERE factor_code LIKE '%GOLD%' OR factor_code LIKE '%SILVER%' OR factor_code LIKE '%au_ag%' OR factor_code LIKE '%AU_AG%'"
try:
    r = pd.read_sql(q, conn)
    print(r.to_string() if len(r) > 0 else '无')
except Exception as e:
    print(e)

# 2. 检查是否有 AG_MACRO 前缀
print()
print("=== AG_MACRO 相关因子 ===")
q2 = "SELECT factor_code, factor_name, direction FROM factor_metadata WHERE factor_code LIKE '%AG_MACRO%'"
try:
    r2 = pd.read_sql(q2, conn)
    print(r2.to_string() if len(r2) > 0 else '无')
except Exception as e:
    print(e)

# 3. 金银比PIT观测
print()
print("=== AG_MACRO_GOLD_SILVER_RATIO 观测 ===")
q3 = "SELECT factor_code, symbol, pub_date, obs_date, raw_value FROM pit_factor_observations WHERE factor_code='AG_MACRO_GOLD_SILVER_RATIO' ORDER BY obs_date DESC LIMIT 5"
try:
    r3 = pd.read_sql(q3, conn)
    print(r3.to_string() if len(r3) > 0 else '无数据')
except Exception as e:
    print(e)

conn.close()

# 4. 检查CU/AL CSV
print()
print("=== CU_AL_ratio.csv ===")
path = r'D:\futures_v6\macro_engine\data\crawlers\shared\daily\CU_AL_ratio.csv'
print('存在: {}'.format(os.path.exists(path)))
if os.path.exists(path):
    df = pd.read_csv(path, parse_dates=['date'])
    print('行数: {}'.format(len(df)))
    print('列名: {}'.format(list(df.columns)))
    print(df.tail(3).to_string())

# 5. 检查AU_AG CSV
print()
print("=== AU_AG_ratio_corrected.csv ===")
path2 = r'D:\futures_v6\macro_engine\data\crawlers\_shared\daily\AU_AG_ratio_corrected.csv'
print('存在: {}'.format(os.path.exists(path2)))
if os.path.exists(path2):
    df2 = pd.read_csv(path2, parse_dates=['date'])
    print('行数: {}'.format(len(df2)))
    print('列名: {}'.format(list(df2.columns)))
    print(df2.tail(3).to_string())
