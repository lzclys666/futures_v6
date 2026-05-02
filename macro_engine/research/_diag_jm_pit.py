"""Diagnose JM spread PIT violations more carefully"""
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import PITDataService
import pandas as pd

pit = PITDataService()
conn = pit._connect()

# 1. Total row count
total = pd.read_sql("SELECT COUNT(*) FROM jm_futures_spread", conn).iloc[0,0]
print(f"Total rows: {total}")

# 2. Count by obs_date
by_obs = pd.read_sql("""
    SELECT obs_date, COUNT(*) as cnt
    FROM jm_futures_spread
    GROUP BY obs_date
    ORDER BY obs_date DESC
""", conn)
print(f"\nBy obs_date ({len(by_obs)} distinct):")
print(by_obs.to_string())

# 3. Count by pub_date
by_pub = pd.read_sql("""
    SELECT pub_date, COUNT(*) as cnt
    FROM jm_futures_spread
    GROUP BY pub_date
    ORDER BY pub_date DESC
""", conn)
print(f"\nBy pub_date ({len(by_pub)} distinct):")
print(by_pub.to_string())

# 4. Count by trade_date
by_trade = pd.read_sql("""
    SELECT trade_date, COUNT(*) as cnt
    FROM jm_futures_spread
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT 20
""", conn)
print(f"\nBy trade_date (top 20):")
print(by_trade.to_string())

# 5. Full violation analysis: pub_date > obs_date
violations = pd.read_sql("""
    SELECT obs_date, pub_date, trade_date, COUNT(*) as cnt
    FROM jm_futures_spread
    WHERE pub_date > obs_date
    GROUP BY obs_date, pub_date, trade_date
    ORDER BY obs_date DESC
    LIMIT 30
""", conn)
print(f"\nAll violations (pub_date > obs_date), {len(violations)} groups:")
print(violations.to_string())
print(f"Total violation rows: {violations['cnt'].sum()}")

# 6. Check obs_date == trade_date after our fix
match = pd.read_sql("""
    SELECT COUNT(*) as cnt FROM jm_futures_spread WHERE obs_date = trade_date
""", conn)
print(f"\nRows where obs_date = trade_date: {match.iloc[0,0]}")

# 7. Check remaining violations after fix
remaining = pd.read_sql("""
    SELECT COUNT(*) as cnt FROM jm_futures_spread WHERE pub_date > obs_date
""", conn)
print(f"Remaining violations: {remaining.iloc[0,0]}")

conn.close()
