from config.paths import MACRO_ENGINE
import sys, sqlite3
sys.path.insert(0, 'str(MACRO_ENGINE)')
from core.analysis.ic_heatmap_service import IcHeatmapService
from datetime import date

svc = IcHeatmapService()

# 查询 pit_factor_observations 中的因子
db = 'str(MACRO_ENGINE)/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# RU 有哪些因子
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol='RU' ORDER BY factor_code")
ru_factors = [r[0] for r in cur.fetchall()]
print('RU factors in observations:', ru_factors)
print('Count:', len(ru_factors))

# 检查每个因子的数据量
for f in ru_factors[:5]:
    cur.execute('SELECT COUNT(*), MIN(obs_date), MAX(obs_date) FROM pit_factor_observations WHERE symbol=? AND factor_code=?', ('RU', f))
    cnt, mn, mx = cur.fetchone()
    print(f'  {f}: {cnt} obs, {mn} to {mx}')

# 测试 calculate_ic with RU factor
print()
for f in ru_factors[:3]:
    result = svc.calculate_ic(f, 'RU', date(2026,1,1), date(2026,4,28))
    if result:
        print(f'{f}: IC={result.ic_value:.4f}, n={result.sample_size}')
    else:
        print(f'{f}: None')

conn.close()
