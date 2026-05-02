"""
Stage 3 探查: PIT IC 相关表 + 评分系统设计
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# 1. ic_heatmap 表结构
print("=== ic_heatmap 结构 ===")
cols = conn.execute('PRAGMA table_info(ic_heatmap)').fetchall()
for c in cols:
    print('  {} {}'.format(c[1], c[2]))

print()
print("=== ic_heatmap 有效(is_mock=0)记录 ===")
real = pd.read_sql(
    "SELECT * FROM ic_heatmap WHERE is_mock=0 AND ic_value IS NOT NULL "
    "ORDER BY calc_date DESC LIMIT 10", conn
)
print(real.to_string() if len(real) > 0 else '无真实 IC 数据')

print()
print("=== ic_heatmap 所有记录 ===")
all_recs = pd.read_sql("SELECT * FROM ic_heatmap ORDER BY calc_date DESC", conn)
print(all_recs.to_string())

# 2. pit_factor_observations 表中已注册的因子
print()
print("=== 已注册的因子 (TOP20 by 表行数) ===")
dist = pd.read_sql(
    "SELECT factor_code, symbol, COUNT(*) as cnt FROM pit_factor_observations "
    "GROUP BY factor_code ORDER BY cnt DESC LIMIT 20",
    conn
)
print(dist.to_string())

conn.close()
