import sys
sys.path.insert(0, 'D:/futures_v6/macro_engine')
from core.analysis.ic_heatmap_service import IcHeatmapService
from datetime import date

svc = IcHeatmapService()

# 测试 get_heatmap_data 用真实因子
print("=== get_heatmap_data 测试 ===")
result = svc.get_heatmap_data(symbols=['RU'], as_of_date=date(2026,4,28), lookback_days=120)
print("Keys:", list(result.keys()))
m = result.get('matrix', [])
print("Matrix rows:", len(m))
print("Sample row:", m[0] if m else "N/A")
flat = [v for row in m for v in row if v is not None]
print(f"Non-None ICs: {len(flat)} of {sum(len(r) for r in m)}")
if flat:
    print("Sample:", flat[:5])

# 测试 get_ic_history
print("\n=== get_ic_history 测试 ===")
h = svc.get_ic_history('RU_FUT_OI', 'RU', date(2026,1,1), date(2026,4,28), rolling_window=20)
print("Keys:", list(h.keys()))
print("IC count:", len(h.get('ic_values', [])))
print("First 5 ICs:", h.get('ic_values', [])[:5])
