"""
离线信号统计脚本
验证权重更新后各品种方向分布
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from macro_scoring_engine import FACTOR_META, get_all_signals

def count_signals():
    counts = {"LONG": 0, "NEUTRAL": 0, "SHORT": 0, "ERROR": 0}
    details = []

    # 先打印当前权重
    print("=" * 60)
    print("当前 FACTOR_META 权重")
    print("=" * 60)
    for sym, groups in FACTOR_META.items():
        print(f"\n{sym}:")
        for f in groups:
            print(f"  {f['factor_code']}: weight={f['weight']} dir={f['direction']}")

    # 调用 get_all_signals 获取信号
    print("\n" + "=" * 60)
    print("信号统计")
    print("=" * 60)

    signals = get_all_signals()
    for sig in signals:
        sym = sig.get("symbol", "?")
        direction = sig.get("direction", "?")
        score = sig.get("compositeScore", 0)
        counts[direction] = counts.get(direction, 0) + 1
        details.append(f"  {sym}: score={score:.4f} -> {direction}")

    for d in details:
        print(d)

    print("-" * 60)
    print(f"结果: LONG={counts['LONG']}  NEUTRAL={counts['NEUTRAL']}  SHORT={counts['SHORT']}")
    print(f"预期: SHORT 约 4 个")
    return counts

if __name__ == "__main__":
    count_signals()
