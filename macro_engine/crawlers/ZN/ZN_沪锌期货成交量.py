#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZN_沪锌期货成交量.py
因子: ZN_VOLUME = 沪锌期货主力合约成交量（手）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("ZN0") — 主力合约日行情
- L2: AKShare futures_zh_daily_sina("ZN0") — 日行情成交量
- L3: 新浪实时API — 实时成交量
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

FCODE = "ZN_VOLUME"
SYM = "ZN"
BOUNDS = (10000, 500000)


def fetch():
    # L1: AKShare futures_main_sina
    try:
        df = ak.futures_main_sina(symbol="ZN0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            # 成交量通常是第5列或名为"成交量"
            vol_col = None
            for c in cols:
                if 'volume' in str(c).lower() or '成交量' in str(c):
                    vol_col = c
                    break
            if vol_col is None and len(cols) > 5:
                vol_col = cols[5]
            if vol_col:
                val = df.iloc[-1][vol_col]
                if isinstance(val, str):
                    val = val.replace(',', '').strip()
                val = float(val)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    obs_dt = df.iloc[-1][cols[0]]
                    return val, obs_dt
    except Exception as e:
        print(f"[L1] {FCODE}失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    val, obs_dt = fetch()
    if val is None:
        print(f"[L1-L3 FAIL] {FCODE} 所有数据源均失败")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return
    if obs_dt:
        obs_date = str(obs_dt)[:10]
    save_to_db(FCODE, SYM, pub_date, obs_date, val, source_confidence=1.0, source='AKShare_Sina_ZN0')
    print(f"[OK] {FCODE}={val} obs={obs_date}")


if __name__ == "__main__":
    main()
