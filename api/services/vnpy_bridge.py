# api/services/vnpy_bridge.py -- re-export bridge
# Avoids circular import by loading the real module from absolute path
import importlib.util, os

_real_path = os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'vnpy_bridge.py')
_spec = importlib.util.spec_from_file_location('_real_vnpy_bridge', _real_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

get_vnpy_bridge = _mod.get_vnpy_bridge
set_vnpy_bridge = _mod.set_vnpy_bridge
VNpyBridge = _mod.VNpyBridge
RiskEvent = _mod.RiskEvent

__all__ = ['get_vnpy_bridge', 'set_vnpy_bridge', 'VNpyBridge', 'RiskEvent']
