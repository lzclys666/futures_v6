# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path

# 动态计算项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent
while not (_PROJECT_ROOT / "macro_engine").exists() and _PROJECT_ROOT != _PROJECT_ROOT.parent:
    _PROJECT_ROOT = _PROJECT_ROOT.parent

conn = sqlite3.connect(str(_PROJECT_ROOT / "macro_engine" / "pit_data.db"))
cur = conn.cursor()

# Check all AU factors
factors = [
    'AU_US_10Y_YIELD', 'AU_FED_RATE', 'AU_SPD_AUAG', 'AU_CFTC_NC',
    'AU_GOLD_RESERVE_CB', 'AU_FUT_CLOSE', 'AU_FUT_OI', 'AU_SPD_BASIS',
    'AU_DXY', 'AU_SPD_GLD', 'AU_SHFE_RANK', 'AU_FED_DOT'
]
for f in factors:
    cur.execute('''SELECT factor_code, obs_date, raw_value, source_confidence 
                   FROM pit_factor_observations 
                   WHERE factor_code=? ORDER BY obs_date DESC LIMIT 1''', (f,))
    row = cur.fetchone()
    if row:
        print('OK:', row[0], '=', row[2], 'obs=', row[1], 'conf=', row[3])
    else:
        print('MISSING:', f)

# Total AU rows
cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol='AU'")
cnt = cur.fetchone()
print('Total AU rows:', cnt[0])

conn.close()

