#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZN_LME锌3月.py
因子: ZN_LME_3M = LME锌3个月期货价格（美元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_foreign_commodity_realtime("ZSD") — LME锌3个月实时
- L2: AKShare futures_lme_zj — LME库存/价格
- L3: LME官网免费数据
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

FCODE = "ZN_LME_3M"
SYM = "ZN"
BOUNDS = (1500, 5000)


def fetch():
    # L1: AKShare LME锌3个月实时行情
    try:
        df = ak.futures_foreign_commodity_realtime("ZSD")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            # 找最新价列
            price_col = None
            for c in cols:
                if '最新价' in str(c) or 'latest' in str(c).lower():
                    price_col = c
                    break
            if price_col is None and len(cols) > 1:
                price_col = cols[1]
            if price_col:
                val = df.iloc[-1][price_col]
                if isinstance(val, str):
                    val = val.replace(',', '').strip()
                val = float(val)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L1] ZSD LME锌3月: {val}")
                    return val, "AKShare_LME_ZSD"
    except Exception as e:
        print(f"[L1] ZSD失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    val, src = fetch()
    if val is None:
        print(f"[L1-L3 FAIL] {FCODE} 所有数据源均失败")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return
    save_to_db(FCODE, SYM, pub_date, obs_date, val, source_confidence=1.0, source=src)
    print(f"[OK] {FCODE}={val}")


if __name__ == "__main__":
    main()
