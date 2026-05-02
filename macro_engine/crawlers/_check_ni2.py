# -*- coding: utf-8 -*-
import sqlite3
db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT factor_code, symbol, raw_value, obs_date, pub_date, source FROM pit_factor_observations WHERE factor_code='NI_SPD_BASIS' ORDER BY pub_date DESC LIMIT 3")
for r in cur.fetchall():
    print(r)
conn.close()
