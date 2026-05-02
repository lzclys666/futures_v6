"""
Stage 2: PIT DB 结构探查 + ratio 因子检查
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

print("=== factor_metadata 结构 ===")
cols = conn.execute('PRAGMA table_info(factor_metadata)').fetchall()
for c in cols:
    pk = 'PK' if c[5] else ''
    print('  {} {} {}'.format(c[1], c[2], pk))

print()
print("=== factor_metadata 示例 (5条) ===")
df = pd.read_sql('SELECT * FROM factor_metadata LIMIT 5', conn)
print(df.to_string())

print()
print("=== pit_factor_observations 结构 ===")
cols2 = conn.execute('PRAGMA table_info(pit_factor_observations)').fetchall()
for c in cols2:
    pk = 'PK' if c[5] else ''
    print('  {} {} {}'.format(c[1], c[2], pk))

print()
print("=== ratio 相关因子 ===")
q = "SELECT factor_code, factor_name, direction, frequency, norm_method, is_active FROM factor_metadata WHERE factor_code LIKE '%ratio%' OR factor_code LIKE '%RATIO%' OR factor_code LIKE '%金银比%'"
try:
    result = pd.read_sql(q, conn)
    print(result.to_string() if len(result) > 0 else '无 ratio 相关因子')
except Exception as e:
    print('Query error: {}'.format(e))

print()
print("=== 宏观/共享类因子 ===")
q2 = "SELECT factor_code, factor_name, direction, frequency FROM factor_metadata WHERE factor_code LIKE '%macro%' OR factor_code LIKE '%MACRO%' OR factor_code LIKE '%shared%' OR factor_code LIKE '%SHARED%'"
try:
    result2 = pd.read_sql(q2, conn)
    print(result2.to_string() if len(result2) > 0 else '无 宏观/共享 因子')
except Exception as e:
    print('Query error: {}'.format(e))

print()
print("=== 金银比因子 ===")
q3 = "SELECT factor_code, factor_name, direction, frequency FROM factor_metadata WHERE factor_code LIKE '%GOLD%' OR factor_code LIKE '%SILVER%'"
try:
    result3 = pd.read_sql(q3, conn)
    print(result3.to_string() if len(result3) > 0 else '无 金银比 因子')
except Exception as e:
    print('Query error: {}'.format(e))

conn.close()
