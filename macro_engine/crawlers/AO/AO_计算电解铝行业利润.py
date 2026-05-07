#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_计算电解铝行业利润.py
因子: AO_PROFIT_AL_SMELT = 电解铝行业利润（元/吨）

公式: 利润 = 沪铝期货价格 × 汇率 - 电解铝完全成本

当前状态: [⚠️待修复]
- L1: AKShare futures_zh_daily_sina(symbol="AL0") 获取沪铝价格，乘以汇率减去成本
- 修复记录: 2026-05-05 futures_main_sina返回ValueError, 改用futures_zh_daily_sina
- 电解铝完全成本按行业平均约16000元/吨（含氧化铝、阳极、电费等）
- 汇率来源: AKShare 或固定值 7.25
- bounds: [-5000, 10000]元/吨
- 注: 成本参数可能需要定期更新

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AO_PROFIT_AL_SMELT"
SYMBOL = "AO"
BOUNDS = (-5_000, 10_000)

# 电解铝完全成本（元/吨），行业平均水平
# 含氧化铝、阳极、冰晶石、电费、人工等
# 需定期更新，当前为2026年Q1行业均值
AL_FULL_COST = 16000.0


def fetch():
    # L1: AKShare 获取沪铝价格
    print("[L1] AKShare futures_zh_daily_sina AL0...")
    try:
        df = ak.futures_zh_daily_sina(symbol="AL0")
        if df is not None and len(df) > 0:
            al_price = float(df.iloc[-1]["close"])
            # 简化计算：沪铝价格直接以人民币计价，无需汇率转换
            # 沪铝本身就是人民币价格
            profit = round(al_price - AL_FULL_COST, 2)
            print(f"[L1] 沪铝价格={al_price:.0f}, 完全成本={AL_FULL_COST:.0f}, 利润={profit:.0f} 元/吨")
            if BOUNDS[0] <= profit <= BOUNDS[1]:
                return profit, "akshare", 0.9
            else:
                print(f"[WARN] 利润={profit} 超出 bounds")
                return profit, "akshare", 0.8
    except Exception as e:
        print(f"[L1] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    val, source, confidence = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(电解铝利润)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
