import sqlite3
conn = sqlite3.connect('D:\\futures_v6\\macro_engine\\pit_data.db')
cur = conn.cursor()

# 95条stub/conf=0.5的因子详情
print("=== Stub记录详情 (conf=0.5) ===")
cur.execute("""
    SELECT symbol, factor_code, source, source_confidence, obs_date, raw_value, pub_date
    FROM pit_factor_observations 
    WHERE source_confidence=0.5
    ORDER BY symbol, factor_code
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}: val={row[5]}, src={row[2]}, obs={row[4]}")

print()
print("=== 缺数据品种统计 ===")
missing = ['AO', 'CU', 'EC', 'EG', 'FU', 'HC', 'I', 'LC', 'LH', 'NI', 'PB', 'PP', 'P', 'SC', 'SN', 'Y', 'ZN']
for sym in missing:
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol=?", (sym,))
    cnt = cur.fetchone()[0]
    cur.execute("SELECT MAX(obs_date) FROM pit_factor_observations WHERE symbol=?", (sym,))
    latest = cur.fetchone()[0] or '无数据'
    print(f"  {sym}: {cnt}条, 最新obs={latest}")
