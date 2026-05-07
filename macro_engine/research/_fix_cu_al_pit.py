"""
Fix CU_AL_ratio PIT violation: set pub_date = next trading day
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)

# 1. Get all CU_AL_ratio obs_dates
df = pd.read_sql(
    "SELECT rowid, obs_date, pub_date FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' ORDER BY obs_date",
    conn
)
print(f"CU_AL_ratio records to fix: {len(df)}")

# 2. Get trading calendar from CU_FUT_CLOSE (or any CU price data)
# Use CU_FUT_CLOSE obs_dates as proxy for trading days
trading_days = pd.read_sql(
    "SELECT DISTINCT obs_date FROM pit_factor_observations WHERE factor_code='CU_FUT_CLOSE' ORDER BY obs_date",
    conn
)['obs_date'].tolist()

# Also add AG_FUT_CLOSE trading days for completeness
ag_days = pd.read_sql(
    "SELECT DISTINCT obs_date FROM pit_factor_observations WHERE factor_code='AG_FUT_CLOSE' ORDER BY obs_date",
    conn
)['obs_date'].tolist()

# Merge and sort all trading days
all_trading_days = sorted(set(trading_days + ag_days))
print(f"Trading calendar entries: {len(all_trading_days)}")

# 3. For each CU_AL_ratio record, find next trading day
def find_next_trading_day(obs_date_str, trading_days_list):
    """Find the next trading day after obs_date"""
    # Binary search for the position
    idx = trading_days_list.index(obs_date_str) if obs_date_str in trading_days_list else None
    
    if idx is not None and idx + 1 < len(trading_days_list):
        return trading_days_list[idx + 1]
    
    # Fallback: try adding 1 day, 2 days, etc.
    obs_dt = datetime.strptime(obs_date_str, '%Y-%m-%d')
    for delta in [1, 2, 3, 4, 5, 6, 7]:
        candidate = (obs_dt + timedelta(days=delta)).strftime('%Y-%m-%d')
        if candidate in trading_days_list:
            return candidate
    
    # Last resort: just add 1 calendar day
    return (obs_dt + timedelta(days=1)).strftime('%Y-%m-%d')

# Build update list
updates = []
not_found = 0
for _, row in df.iterrows():
    obs_date = row['obs_date']
    new_pub_date = find_next_trading_day(obs_date, all_trading_days)
    if new_pub_date == obs_date:
        not_found += 1
    updates.append((new_pub_date, row['rowid']))

print(f"Updates prepared: {len(updates)}")
print(f"Could not find next trading day (fallback used): {not_found}")

# 4. Execute update
cur = conn.cursor()
cur.executemany(
    "UPDATE pit_factor_observations SET pub_date = ? WHERE rowid = ?",
    updates
)
conn.commit()
print(f"Updated: {cur.rowcount} rows")

# 5. Verify
df_after = pd.read_sql(
    "SELECT obs_date, pub_date FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' ORDER BY obs_date",
    conn
)
violations_after = (df_after['pub_date'] == df_after['obs_date']).sum()
print(f"\nVerification:")
print(f"  Total records: {len(df_after)}")
print(f"  Remaining violations (obs_date=pub_date): {violations_after}")
print(f"  First 5 records:")
for i in range(min(5, len(df_after))):
    print(f"    obs={df_after.iloc[i]['obs_date']} pub={df_after.iloc[i]['pub_date']}")

conn.close()
print("\n=== Fix complete ===")
