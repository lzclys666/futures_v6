import sys
sys.path.insert(0, 'D:/futures_v6/macro_engine')
sys.path.insert(0, 'D:/futures_v6')

from macro_engine.core.analysis.ic_heatmap_service import IcHeatmapService

print("Import OK:", IcHeatmapService)
import inspect
print("File:", inspect.getfile(IcHeatmapService))
