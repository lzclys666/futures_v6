import sys
from pathlib import Path
sys.path.insert(0, r'D:\futures_v6\api')
sys.path.insert(0, r'D:\futures_v6\macro_engine')
sys.path.insert(0, r'D:\futures_v6')

import datetime
from macro_engine.core.analysis.ic_heatmap_service import IcHeatmapService

svc = IcHeatmapService()
res = svc.get_heatmap_data(['RU'], datetime.date(2026, 4, 28), 120)
print('factors:', res['factors'][:5])
flat = [v for row in res['matrix'] for v in row if v is not None]
print(f'total={len(res["factors"])}, nonNone={len(flat)}')
