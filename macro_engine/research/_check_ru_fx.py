"""Check RU_FX_USDCNY PIT violations"""
import sqlite3

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# Check RU violations
cur.execute(
    "SELECT factor_code, "
    "SUM(CASE WHEN obs_date = pub_date THEN 1 ELSE 0 END) AS violations, "
    "COUNT(*) AS total "
    "FROM pit_factor_observations WHERE symbol='RU' "
    "GROUP BY factor_code ORDER BY violations DESC"
)
print("RU factors with violations:")
for row in cur.fetchall():
    if row[1] > 0:
        print(f"  {row[0]:25s} {row[1]:>6} / {row[2]:>6}")

# Check if RU_FX_USDCNY exists
cur.execute(
    "SELECT factor_code, symbol, COUNT(*) FROM pit_factor_observations "
    "WHERE factor_code LIKE '%USD%' OR factor_code LIKE '%FX%' "
    "GROUP BY factor_code, symbol"
)
print("\nUSD/FX related factors:")
for row in cur.fetchall():
    print(f"  {row[0]:25s} {row[1]:5s} {row[2]:>6}")

conn.close()
