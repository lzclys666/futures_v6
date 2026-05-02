import sys
# 模拟 API server 的 sys.path
sys.path.insert(0, 'D:/futures_v6/macro_engine')  # 先加 macro_engine
sys.path.insert(0, 'D:/futures_v6/api')
sys.path.insert(0, 'D:/futures_v6')

# 尝试显式导入 macro_engine.core
try:
    from macro_engine.core.analysis.ic_heatmap_service import IcHeatmapService as RealSvc
    print("OK - Real IcHeatmapService")
    import inspect
    print("File:", inspect.getfile(RealSvc))
except ImportError as e:
    print("FAIL:", e)

# 验证当前 ic_heatmap.py 的导入会解析到哪里
try:
    from core.analysis.ic_heatmap_service import IcHeatmapService as StubSvc
    import inspect
    print("core.analysis resolves to:", inspect.getfile(StubSvc))
except ImportError as e:
    print("core.analysis FAIL:", e)
