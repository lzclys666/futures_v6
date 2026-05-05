#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取铝土矿进口量.py
因子: AO_IMP_BAUXITE = 中国铝土矿进口量（万吨/月）

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: AKShare 尝试海关进出口数据接口
- L2: 新闻/行业网站备用
- L3: save_l4_fallback() 兜底
- bounds: [0, 2000]万吨/月
- 注: 海关数据为月度，通常滞后1-2个月

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AO_IMP_BAUXITE"
SYMBOL = "AO"
BOUNDS = (0, 2_000)  # 万吨/月


def fetch():
    # L1: AKShare 海关数据
    print("[L1] AKShare 海关进出口数据...")
    try:
        df = ak.macro_china_imports(index="铝矿砂及其精矿")
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1]["value"])
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L1] 成功: {val:.2f} 万吨/月")
                return val, "akshare_customs", 0.9
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 备用接口
    print("[L2] AKShare 备用接口...")
    try:
        df = ak.macro_china_trade_balance(index="铝矿砂")
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1].get("进口量", df.iloc[-1].iloc[1]))
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L2] 成功: {val:.2f} 万吨/月")
                return val, "akshare_trade", 0.8
    except Exception as e:
        print(f"[L2] 失败: {e}")

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

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(铝土矿进口量)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} 无可用数据源")


if __name__ == "__main__":
    main()
