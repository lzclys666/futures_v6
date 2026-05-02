import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cur = conn.cursor()

# Check ZN_LME factors
cur.execute("SELECT factor_code, obs_date, raw_value FROM pit_factor_observations WHERE factor_code LIKE 'ZN_LME%' ORDER BY obs_date DESC LIMIT 5")
print('ZN_LME factors:')
for row in cur.fetchall():
    print(f'  {row}')

# Check AU/AG factors
cur.execute("SELECT factor_code, obs_date, raw_value FROM pit_factor_observations WHERE factor_code LIKE 'AU_%' OR factor_code LIKE 'AG_%' ORDER BY obs_date DESC LIMIT 10")
print()
print('AU/AG factors:')
for row in cur.fetchall():
    print(f'  {row}')

# Check PMI factors
cur.execute("SELECT factor_code, obs_date, raw_value FROM pit_factor_observations WHERE factor_code LIKE '%PMI%' ORDER BY obs_date DESC LIMIT 5")
print()
print('PMI factors:')
for row in cur.fetchall():
    print(f'  {row}')

# Check SOYBEAN factors
cur.execute("SELECT factor_code, obs_date, raw_value FROM pit_factor_observations WHERE factor_code LIKE '%SOYBEAN%' OR factor_code LIKE 'Y_%' ORDER BY obs_date DESC LIMIT 5")
print()
print('SOYBEAN factors:')
for row in cur.fetchall():
    print(f'  {row}')

conn.close()
