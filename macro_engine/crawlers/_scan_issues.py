# -*- coding: utf-8 -*-
"""全面扫描因子数据质量问题"""
import sqlite3
from datetime import date, timedelta

db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

today = date.today()
week_ago = (today - timedelta(days=7)).isoformat()
month_ago = (today - timedelta(days=30)).isoformat()

print("=== 因子数据质量扫描 ===\n")

# 1. 近7天数据按品种统计
print("【各品种近7天有数据的因子数】")
cur.execute(f"""
SELECT symbol, COUNT(DISTINCT factor_code) as cnt 
FROM pit_factor_observations 
WHERE obs_date >= '{week_ago}'
GROUP BY symbol 
ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} 个因子")

# 2. 查找L4因子（conf <= 0.5）
print("\n【L4回补/低置信度因子（conf <= 0.5）】")
cur.execute(f"""
SELECT DISTINCT factor_code, symbol, raw_value, obs_date, source_confidence
FROM pit_factor_observations 
WHERE obs_date >= '{month_ago}' AND source_confidence <= 0.5
ORDER BY symbol, factor_code
""")
for r in cur.fetchall():
    print(f"  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]}, conf={r[4]})")

# 3. 查找0值因子（可能是placeholder）
print("\n【零值或接近零的因子（可能是placeholder）】")
cur.execute(f"""
SELECT factor_code, symbol, raw_value, obs_date
FROM pit_factor_observations 
WHERE obs_date >= '{month_ago}' AND ABS(raw_value) < 0.001
ORDER BY symbol, factor_code
""")
for r in cur.fetchall():
    print(f"  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]})")

# 4. 查找obs_date明显过旧的因子
print("\n【obs_date过旧（30天以上未更新）】")
old_date = (today - timedelta(days=30)).isoformat()
cur.execute(f"""
SELECT DISTINCT factor_code, symbol, raw_value, obs_date, 
       CAST(julianday('now') - julianday(obs_date) AS INTEGER) as days_old
FROM pit_factor_observations 
WHERE obs_date < '{old_date}'
ORDER BY days_old DESC
LIMIT 20
""")
for r in cur.fetchall():
    print(f"  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]}, {r[4]}天前)")

# 5. 检查source为空字符串的记录
print("\n【source字段为空的记录】")
cur.execute(f"""
SELECT DISTINCT factor_code, symbol, raw_value, obs_date
FROM pit_factor_observations 
WHERE obs_date >= '{month_ago}' AND (source IS NULL OR source = '')
LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[0]} [{r[1]}] = {r[2]} (obs={r[3]})")

conn.close()
