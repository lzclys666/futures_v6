"""检查 CU_FUT_CLOSE 数据"""
import sqlite3, pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
df = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_FUT_CLOSE' AND symbol='CU' "
    "ORDER BY obs_date DESC LIMIT 10",
    conn)
print('CU_FUT_CLOSE 最新10行:')
print(df.to_string())

# 检查是否有其他日期的CLOSE
cnt = pd.read_sql(
    "SELECT COUNT(*) FROM pit_factor_observations "
    "WHERE factor_code='CU_FUT_CLOSE' AND symbol='CU'",
    conn).fetchone()[0]
print('\nCU_FUT_CLOSE 总行数:', cnt)

# 查所有CU_CLOSE变体
variants = pd.read_sql(
    "SELECT factor_code, symbol, COUNT(*) as cnt FROM pit_factor_observations "
    "WHERE symbol='CU' AND (factor_code LIKE '%CLOSE%' OR factor_code LIKE '%close%') "
    "GROUP BY factor_code, symbol",
    conn)
print('\nCU CLOSE变体:')
print(variants.to_string())

conn.close()
