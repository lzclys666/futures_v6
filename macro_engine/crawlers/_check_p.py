# -*- coding: utf-8 -*-
import sqlite3
db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for fc in ['P_SPD_BASIS', 'P_SPD_CONTRACT']:
    cur.execute(f"SELECT factor_code, symbol, raw_value, obs_date, pub_date, source FROM pit_factor_observations WHERE factor_code='{fc}' ORDER BY pub_date DESC LIMIT 3")
    print(f'--- {fc} ---')
    for r in cur.fetchall():
        print(r)
conn.close()
