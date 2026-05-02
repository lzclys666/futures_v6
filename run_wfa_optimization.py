# run_wfa_sequential.py
"""
多因子策略 Walk-Forward 分析 (单线程顺序版)
彻底解决 vnpy_ctabacktester 内部多线程 engine 为 None 的问题
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Any
import itertools

# 策略路径
STRATEGY_PATH = r"C:\Users\Administrator\strategies"
if STRATEGY_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_PATH)

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval
from vnpy_ctabacktester import CtaBacktesterApp

try:
    from dateutil.relativedelta import relativedelta
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

# ==================== 配置参数 ====================
VT_SYMBOL = "rb2510.SHFE"
INTERVAL = Interval.MINUTE
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

TRAIN_MONTHS = 6
TEST_MONTHS = 3
STEP_MONTHS = 3

CAPITAL = 1_000_000
RATE = 0.0001
SLIPPAGE = 1.0
SIZE = 10
PRICETICK = 1.0

OPTIMIZATION_PARAMS_SPACE = {
    "long_threshold": [0.3, 0.5, 0.7],
    "short_threshold": [-0.7, -0.5, -0.3],
    "weight_trend": [0.3, 0.5],
    "weight_momentum": [0.2, 0.4],
}
OPTIMIZATION_TARGET = "sharpe_ratio"

FIXED_PARAMS = {
    "fixed_volume": 1,
    "observe_weight_coef": 0.3,
    "observe_stop_mult": 1.3,
    "stop_loss_atr_mult": 2.0,
    "take_profit_atr_mult": 3.0,
    "local_monitor_symbols": "jm,lh,zn,br,sa,ec"
}

OUTPUT_FILE = "wfa_results.json"

# ==================== 辅助函数 ====================
def add_months(dt: datetime, months: int) -> datetime:
    if HAS_DATEUTIL:
        return dt + relativedelta(months=months)
    else:
        return dt + timedelta(days=months * 30)

def generate_windows(start: datetime, end: datetime) -> List[Tuple[datetime, datetime, datetime, datetime]]:
    windows = []
    current = start
    while True:
        train_end = add_months(current, TRAIN_MONTHS)
        test_start = train_end
        test_end = add_months(test_start, TEST_MONTHS)
        if test_end > end:
            break
        windows.append((current, train_end, test_start, test_end))
        current = add_months(current, STEP_MONTHS)
    return windows

def generate_param_combinations(param_space: Dict) -> List[Dict]:
    keys = list(param_space.keys())
    values = list(param_space.values())
    combos = []
    for combo in itertools.product(*values):
        combos.append({keys[i]: combo[i] for i in range(len(keys))})
    return combos

def run_single_backtest(params: Dict, start: datetime, end: datetime) -> Optional[Dict]:
    """单次回测，顺序执行，无多线程干扰"""
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_app(CtaBacktesterApp)
    engine = main_engine.get_engine("CtaBacktester")
    if engine is None:
        for name, eng in main_engine.engines.items():
            if 'Backtester' in name:
                engine = eng
                break
    if engine is None:
        return None

    try:
        engine.start_backtesting(
            class_name="MultiFactorStrategy",
            vt_symbol=VT_SYMBOL,
            interval=INTERVAL,
            start=start,
            end=end,
            rate=RATE,
            slippage=SLIPPAGE,
            size=SIZE,
            pricetick=PRICETICK,
            capital=CAPITAL,
            setting=params
        )
        # 等待回测线程结束 (vnpy内部是同步阻塞的，这里无需额外处理)
        stats = engine.get_result_statistics()
        return stats
    except Exception as e:
        print(f"      回测异常: {e}")
        return None

def manual_optimization(train_start: datetime, train_end: datetime) -> Optional[Tuple[Dict, float]]:
    combos = generate_param_combinations(OPTIMIZATION_PARAMS_SPACE)
    total = len(combos)
    print(f"  参数组合总数: {total}")

    best_params = None
    best_target = -float('inf')

    for idx, params in enumerate(combos):
        if (idx + 1) % 5 == 0 or idx == 0:
            print(f"    进度: {idx+1}/{total}")

        full_params = params.copy()
        full_params.update(FIXED_PARAMS)

        stats = run_single_backtest(full_params, train_start, train_end)
        if stats is None:
            continue

        target = stats.get(OPTIMIZATION_TARGET)
        if target is None:
            continue

        if target > best_target:
            best_target = target
            best_params = params

    if best_params is None:
        print("  ❌ 未找到有效参数组合")
        return None
    return best_params, best_target

def convert_datetimes(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_datetimes(item) for item in obj]
    return obj

# ==================== 主流程 ====================
def main():
    print("=" * 70)
    print("🚀 多因子策略 Walk-Forward 分析 (单线程顺序版)")
    print("=" * 70)

    windows = generate_windows(START_DATE, END_DATE)
    print(f"📅 共生成 {len(windows)} 个滚动窗口")
    if not windows:
        print("❌ 无窗口，检查日期范围")
        return

    all_results = []

    for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
        print("\n" + "-" * 50)
        print(f"📌 窗口 {i+1}/{len(windows)}")
        print(f"   训练期: {train_start.date()} -> {train_end.date()}")
        print(f"   测试期: {test_start.date()} -> {test_end.date()}")

        print("   🔍 参数网格搜索...")
        opt_result = manual_optimization(train_start, train_end)

        if opt_result is None:
            print("   ⚠️ 优化失败，跳过本窗口")
            continue

        best_params, best_target = opt_result
        print(f"   🏆 最优参数: {best_params}")
        print(f"   🎯 最优目标: {best_target:.4f}")

        final_params = best_params.copy()
        final_params.update(FIXED_PARAMS)

        print("   📊 样本外回测...")
        out_stats = run_single_backtest(final_params, test_start, test_end)

        if out_stats is None:
            print("   ❌ 样本外回测失败")
            continue

        total_return = out_stats.get('total_return', 'N/A')
        sharpe = out_stats.get('sharpe_ratio', 'N/A')
        max_dd = out_stats.get('max_drawdown', 'N/A')
        print(f"   📈 总收益率: {total_return}% | 夏普: {sharpe} | 最大回撤: {max_dd}%")

        window_result = {
            "window_id": i + 1,
            "train_start": train_start.isoformat(),
            "train_end": train_end.isoformat(),
            "test_start": test_start.isoformat(),
            "test_end": test_end.isoformat(),
            "best_params": best_params,
            "best_target": best_target,
            "out_of_sample_stats": out_stats
        }
        all_results.append(window_result)

    print("\n" + "=" * 70)
    print("📊 Walk-Forward 分析结果汇总")
    print("=" * 70)

    if not all_results:
        print("❌ 没有成功完成任何窗口的分析。")
        return

    total_returns = [r['out_of_sample_stats'].get('total_return', 0) for r in all_results]
    sharpes = [r['out_of_sample_stats'].get('sharpe_ratio', 0) for r in all_results]
    max_drawdowns = [r['out_of_sample_stats'].get('max_drawdown', 0) for r in all_results]

    avg_return = sum(total_returns) / len(total_returns)
    avg_sharpe = sum(sharpes) / len(sharpes)
    avg_max_dd = sum(max_drawdowns) / len(max_drawdowns)

    print(f"📈 样本外平均总收益率: {avg_return:.2f}%")
    print(f"📊 样本外平均夏普比率: {avg_sharpe:.2f}")
    print(f"📉 样本外平均最大回撤: {avg_max_dd:.2f}%")

    serializable_results = convert_datetimes(all_results)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=4, ensure_ascii=False)
    print(f"\n💾 详细结果已保存至: {os.path.abspath(OUTPUT_FILE)}")
    print("\n✅ Walk-Forward 分析完成！")

if __name__ == "__main__":
    main()