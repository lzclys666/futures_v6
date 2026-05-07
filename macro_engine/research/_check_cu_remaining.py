"""Check remaining CU violations after fix"""
import sqlite3

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()
cur.execute(
    "SELECT factor_code, obs_date, pub_date, raw_value FROM pit_factor_observations "
    "WHERE symbol='CU' AND obs_date=pub_date ORDER BY obs_date"
)
for row in cur.fetchall():
    print(f"{row[0]:25s} obs={row[1]} pub={row[2]} val={row[3]}")
conn.close()
