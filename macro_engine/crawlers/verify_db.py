import sqlite3
from pathlib import Path

# 动态计算项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent
while not (_PROJECT_ROOT / "macro_engine").exists() and _PROJECT_ROOT != _PROJECT_ROOT.parent:
    _PROJECT_ROOT = _PROJECT_ROOT.parent

conn = sqlite3.connect(str(_PROJECT_ROOT / "macro_engine" / "pit_data.db"))
cur = conn.cursor()

cur.execute("SELECT factor_code, symbol, obs_date, raw_value, source FROM pit_factor_observations WHERE pub_date='2026-04-20' ORDER BY factor_code")
rows = cur.fetchall()
print('Today records:', len(rows))
for r in rows:
    print(' ', r)

conn.close()
