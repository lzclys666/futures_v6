from config.paths import MACRO_ENGINE
import sys
print('sys.path[0]:', sys.path[0])
print('sys.path[1]:', sys.path[1] if len(sys.path) > 1 else 'N/A')

sys.path.insert(0, 'str(MACRO_ENGINE)')
print()
print('After inserting macro_engine:')
print('sys.path[0]:', sys.path[0])

from core.analysis.ic_heatmap_service import IcHeatmapService
print()
print('Module file:', __import__('core.analysis.ic_heatmap_service').__file__)

svc = IcHeatmapService()
print('svc type:', type(svc))

try:
    series = svc._get_factor_series
    print('_get_factor_series type:', type(series))
except AttributeError as e:
    print('AttributeError:', e)
