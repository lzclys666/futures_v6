import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

codes = ['CU_AL_ratio', 'AG_MACRO_GOLD_SILVER_RATIO', 'AG_COST_USDCNY', 'FU_WTI_PRICE']
for code in codes:
    cur.execute("SELECT COUNT(*), MIN(obs_date), MAX(obs_date) FROM pit_factor_observations WHERE factor_code=?", (code,))
    row = cur.fetchone()
    print(f"{code}: {row[0]} rows, {row[1]} ~ {row[2]}")

conn.close()
