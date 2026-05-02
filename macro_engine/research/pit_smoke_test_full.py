import sqlite3
db_path = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== PIT Smoke Test ===\n")

# 1. 基本统计
cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
total = cur.fetchone()[0]
print(f"1. Total records: {total}")

# 2. 最新数据日期
cur.execute("SELECT MAX(obs_date) FROM pit_factor_observations")
max_obs = cur.fetchone()[0]
print(f"2. Max obs_date: {max_obs}")

cur.execute("SELECT MAX(pub_date) FROM pit_factor_observations")
max_pub = cur.fetchone()[0]
print(f"3. Max pub_date: {max_pub}")

# 3. 今日数据
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE obs_date='2026-04-27'")
today_obs = cur.fetchone()[0]
print(f"4. 2026-04-27 obs records: {today_obs}")

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE pub_date='2026-04-27'")
today_pub = cur.fetchone()[0]
print(f"5. 2026-04-27 pub records: {today_pub}")

# 4. 未来数据（PIT核心检查）
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE obs_date > '2026-04-27'")
future_obs = cur.fetchone()[0]
print(f"6. Future obs_date (>2026-04-27): {future_obs}")

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE pub_date > '2026-04-27'")
future_pub = cur.fetchone()[0]
print(f"7. Future pub_date (>2026-04-27): {future_pub}")

# 5. NULL检查
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE raw_value IS NULL")
null_val = cur.fetchone()[0]
print(f"8. NULL raw_value: {null_val}")

# 6. 置信度检查
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE source_confidence IS NULL OR source_confidence < 0")
bad_conf = cur.fetchone()[0]
print(f"9. Invalid confidence: {bad_conf}")

# 7. CU样本
cur.execute("SELECT obs_date, factor_code, raw_value FROM pit_factor_observations WHERE symbol='CU' ORDER BY obs_date DESC LIMIT 5")
print("\n10. CU latest records:")
for row in cur.fetchall():
    print(f"    {row}")

# 8. 数据覆盖品种
cur.execute("SELECT DISTINCT symbol FROM pit_factor_observations")
symbols = sorted([r[0] for r in cur.fetchall()])
print(f"\n11. Symbols covered: {len(symbols)}")
print(f"    {symbols}")

conn.close()

print("\n=== RESULT ===")
all_pass = (future_obs == 0 and future_pub == 0 and null_val == 0 and bad_conf == 0)
if all_pass:
    print("ALL PIT CHECKS PASSED - Data is PIT compliant")
else:
    print("SOME CHECKS FAILED - Review above output")
