import sqlite3
from pathlib import Path

# 动态计算项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent
while not (_PROJECT_ROOT / "macro_engine").exists() and _PROJECT_ROOT != _PROJECT_ROOT.parent:
    _PROJECT_ROOT = _PROJECT_ROOT.parent

conn = sqlite3.connect(str(_PROJECT_ROOT / "macro_engine" / "pit_data.db"))
cur = conn.cursor()

for prefix in ['P_', 'EG_', 'PP_', 'HC_', 'FU_', 'PB_', 'Y_']:
    cur.execute(f"SELECT factor_code FROM pit_factor_observations WHERE factor_code LIKE '{prefix}%' ORDER BY factor_code")
    rows = [r[0] for r in cur.fetchall()]
    print(f'{prefix} factors: {rows}')

conn.close()
