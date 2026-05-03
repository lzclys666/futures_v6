# -*- coding: utf-8 -*-
from config.paths import PIT_DB
import sqlite3
conn = sqlite3.connect(str(PIT_DB))
cur = conn.cursor()

for prefix in ['P_', 'EG_', 'PP_', 'HC_', 'FU_', 'PB_', 'Y_']:
    cur.execute(f"SELECT factor_code FROM pit_factor_observations WHERE factor_code LIKE '{prefix}%' ORDER BY factor_code")
    rows = [r[0] for r in cur.fetchall()]
    print(f'{prefix} factors: {rows}')

conn.close()
