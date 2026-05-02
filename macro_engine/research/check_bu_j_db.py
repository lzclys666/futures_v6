import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

cur.execute("SELECT obs_date, COUNT(*) FROM pit_factor_observations WHERE symbol IN ('BU','J') GROUP BY obs_date ORDER BY obs_date DESC LIMIT 10")
print("BU/J obs_date counts:")
for r in cur.fetchall():
    print(f"  {r}")

cur.execute("SELECT symbol, COUNT(*) FROM pit_factor_observations WHERE symbol IN ('BU','J') GROUP BY symbol")
print("\nBU/J total records:")
for r in cur.fetchall():
    print(f"  {r}")

# Check latest BU data
cur.execute("SELECT obs_date, factor_code, raw_value, source_confidence FROM pit_factor_observations WHERE symbol='BU' ORDER BY obs_date DESC LIMIT 5")
print("\nBU latest records:")
for r in cur.fetchall():
    print(f"  {r}")

# Check latest J data
cur.execute("SELECT obs_date, factor_code, raw_value, source_confidence FROM pit_factor_observations WHERE symbol='J' ORDER BY obs_date DESC LIMIT 5")
print("\nJ latest records:")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
