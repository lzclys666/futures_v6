from config.paths import PROJECT_ROOT
from config.paths import MACRO_ENGINE
import sys
sys.path.insert(0, 'str(MACRO_ENGINE)')
sys.path.insert(0, str(PROJECT_ROOT))

from macro_engine.core.analysis.ic_heatmap_service import IcHeatmapService

print("Import OK:", IcHeatmapService)
import inspect
print("File:", inspect.getfile(IcHeatmapService))
