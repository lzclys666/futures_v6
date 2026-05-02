# -*- coding: utf-8 -*-
"""因子数据质量汇总"""
import sqlite3
from datetime import date, timedelta

db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

today = date.today()
month_ago = (today - timedelta(days=30)).isoformat()
week_ago = (today - timedelta(days=7)).isoformat()

print("=== 因子健康状况汇总 ===\n")

# 各品种因子总数和健康比例
print("【各品种因子健康状况（近30天有数据）】")
cur.execute(f"""
SELECT 
    symbol,
    COUNT(DISTINCT factor_code) as total,
    SUM(CASE WHEN obs_date >= '{week_ago}' THEN 1 ELSE 0 END) as recent
FROM pit_factor_observations 
GROUP BY symbol 
ORDER BY total DESC
""")
for r in cur.fetchall():
    pct = f"{100*r[2]/r[1]:.0f}%" if r[1] > 0 else "0%"
    print(f"  {r[0]}: {r[2]}/{r[1]} ({pct}) 有近7天数据")

# 需要永久跳过的因子（基于已知数据源失效）
print("\n【需标记为⛔永久跳过的因子（数据源已确认失效）】")
known_skip = [
    ('AL_INV_SHFE', 'AL', 'SHFE仓单接口失效（AKShare futures_shfe_warehouse_receipt返回空）'),
    ('RB_INV_SHFE', 'RB', 'SHFE仓单接口失效'),
    ('NI_SPD_BASIS', 'NI', 'AKShare只返回到2024-04-30的历史数据，无当前免费源'),
    ('P_SPD_BASIS', 'P', 'AKShare只返回到2024-04-30的历史数据，无当前免费源'),
    ('P_SPD_CONTRACT', 'P', '同P_SPD_BASIS'),
    ('AU_SHFE_OI_RANK', 'AU', 'SHFE持仓排名接口失效（AKShare仅支持DCE不支持SHFE）'),
    ('AU_SPD_GLD', 'AU', 'SPDR网站改版404，Yahoo Finance 403，无免费源'),
    ('AU_FED_DOT', 'AU', 'FOMC projections页面404/403，无免费源'),
]
for fc, sym, reason in known_skip:
    print(f"  {fc} [{sym}]: {reason}")

# L4回补因子（需要确认是否应该跳过）
print("\n【L4回补因子（conf<=0.5，需人工确认）】")
l4_factors = {}
cur.execute(f"""
SELECT factor_code, symbol, MAX(obs_date) as last_obs, 
       CAST(julianday('now') - julianday(MAX(obs_date)) AS INTEGER) as days_old,
       raw_value
FROM pit_factor_observations 
WHERE obs_date >= '{month_ago}' AND source_confidence <= 0.5
GROUP BY factor_code, symbol
ORDER BY days_old DESC
""")
for r in cur.fetchall():
    fc, sym, last_obs, days_old, val = r
    if days_old > 7:  # 只关心7天以上未更新的
        print(f"  {fc} [{sym}]: last_obs={last_obs}, {days_old}天前, val={val}")

conn.close()
