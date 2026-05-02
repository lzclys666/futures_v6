"""Debug PIT query for CU_AL_ratio"""
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# ratio 相关因子
q = """SELECT factor_code, symbol, COUNT(*) as cnt 
       FROM pit_factor_observations 
       WHERE factor_code LIKE '%ratio%' OR factor_code LIKE '%RATIO%'
       GROUP BY factor_code, symbol"""
r = pd.read_sql(q, conn)
print('ratio相关因子:')
print(r.to_string())

# 精确查
cnt = conn.execute(
    "SELECT COUNT(*) FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' AND symbol='CU'"
).fetchone()[0]
print('\nCU_AL_ratio + CU 精确查:', cnt)

# 任意CU/Al
cnt2 = conn.execute(
    "SELECT COUNT(*) FROM pit_factor_observations WHERE factor_code LIKE '%CU%AL%'"
).fetchone()[0]
print('CU%AL% 模糊查:', cnt2)

# 查AG相关的
print('\nAG相关因子:')
q2 = """SELECT factor_code, symbol, COUNT(*) as cnt 
        FROM pit_factor_observations 
        WHERE factor_code LIKE '%AG%' OR factor_code LIKE '%ag%'
        GROUP BY factor_code, symbol ORDER BY cnt DESC LIMIT 10"""
r2 = pd.read_sql(q2, conn)
print(r2.to_string())

conn.close()
