"""
Stage 3 验证脚本：CU_FUT_CLOSE 数据质量 + score_multiple 批量接口
"""
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from _stage3_signal_scorer import (
    SignalScorer, _load_factor_pit, _load_price_pit, _compute_ic_stats
)
import sqlite3
import pandas as pd
import numpy as np

DB = r'D:\futures_v6\macro_engine\pit_data.db'

# =========================================================================
# 任务1: CU_FUT_CLOSE 数据质量验证
# =========================================================================
print("=" * 60)
print("任务1: CU_FUT_CLOSE 重复日期影响验证")
print("=" * 60)

conn = sqlite3.connect(DB)

# 检查：CU_FUT_CLOSE 原始行数 vs 去重后
raw = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_FUT_CLOSE' AND symbol='CU'",
    conn)
raw['date'] = pd.to_datetime(raw['obs_date'])
print(f"原始行数: {len(raw)}, 唯—日期数: {raw['date'].nunique()}")
print(f"重复: {len(raw) - raw['date'].nunique()} 行（每日2条相同价格）")

# 检查：去重(keep='first') 是否损失有效数据
deduped = raw.drop_duplicates('date', keep='first')
print(f"去重后: {len(deduped)} 行（保留第一条，等效去重）")
print(f"损失: {len(raw) - len(deduped)} 行 = {len(raw) - len(deduped)} 个重复日期")

# 验证：重复行的 raw_value 是否完全相同
dup_grp = raw.groupby('date')['raw_value'].agg(['count', 'nunique'])
all_same = (dup_grp['nunique'] == 1).all()
all_double = (dup_grp['count'] == 2).all()
print(f"\n每日期2条: {all_double}, 每日期同值: {all_same}")
print(f"结论: drop_duplicates(keep='first') 等效去重，{'无' if all_same else '有'}数据损失")

# 验证：去重后价格数据连续性
deduped_sorted = deduped.set_index('date').sort_index()
price_gaps = deduped_sorted['raw_value'].index.to_series().diff()
large_gaps = price_gaps[price_gaps.dt.days > 5]
if len(large_gaps) > 0:
    print(f"\n警告: 发现 {len(large_gaps)} 个大跳（>5交易日），可能影响IC计算")
    print(large_gaps.head(5).to_string())
else:
    print(f"\n价格数据连续性: OK（无大跳）")

conn.close()

# =========================================================================
# 任务2: score_multiple 批量评分接口验证
# =========================================================================
print("\n" + "=" * 60)
print("任务2: score_multiple 批量评分验证")
print("=" * 60)

scorer = SignalScorer()

# 测试批量评分：CU + 多个因子
factor_list = [
    ('CU_AL_ratio', 1, 10),
    ('CU_AL_ratio', 1, 20),
    # ('AG_MACRO_GOLD_SILVER_RATIO', -1, 10),
    # ('CU_LME_SPREAD_DIFF', 1, 10),
]

results = scorer.score_multiple(factor_list, 'CU')
print(f"\n批量评分结果（{len(results)}个因子）:")
for i, r in enumerate(results):
    print(f"\n  [{i+1}] {r['factor_code']} hold={r['hold_days']}d")
    if 'error' in r:
        print(f"      ERROR: {r['error']}")
    else:
        print(f"      Signal={r['signal']} Score={r['total_score']}/100")
        print(f"      IC: mean={r['ic_stats']['ic_mean']:.4f} "
              f"IR={r['ic_stats']['ic_ir']:.4f} "
              f"win={r['ic_stats']['ic_win']:.1%} n={r['ic_stats']['ic_n']}")
        print(f"      数据: factor={r['factor_latest']} price={r['price_latest']}")
        print(f"      分数明细: {r['components']}")

# =========================================================================
# 任务3: 修正后的 IC 数据质量（确认10d vs 20d方向差异）
# =========================================================================
print("\n" + "=" * 60)
print("任务3: 深度分析 CU/AL ratio IC 持有期差异")
print("=" * 60)

# 加载重叠数据
fser = _load_factor_pit(DB, 'CU_AL_ratio', 'CU', lookback=500)
pser = _load_price_pit(DB, 'CU', lookback=500)

if fser is not None and pser is not None:
    df = pd.DataFrame({'f': fser, 'p': pser})
    df = df[~df.index.duplicated(keep='first')].dropna()
    print(f"重叠数据: {len(df)} 行")
    print(f"  因子: {fser.index[0].date()} ~ {fser.index[-1].date()}")
    print(f"  价格: {pser.index[0].date()} ~ {pser.index[-1].date()}")

    for hold in [5, 10, 15, 20, 30]:
        ic_s, ic_m, ic_std, ic_w = _compute_ic_stats(fser, pser, window=60, hold=hold)
        if len(ic_s) > 5:
            print(f"  hold={hold:2d}d: IC={ic_m:+.4f} IR={ic_m/ic_std if ic_std>0 else 0:+.4f} "
                  f"win={ic_w:.1%} n={len(ic_s)}")
else:
    print(f"  数据加载失败: fser={fser is None}, pser={pser is None}")

print("\nDone.")
