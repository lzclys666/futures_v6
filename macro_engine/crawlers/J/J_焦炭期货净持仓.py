#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期货净持仓.py
因子: J_POS_NET = 焦炭期货净持仓

公式: J_POS_NET = 多头持仓 - 空头持仓（手）

当前状态: [⚠️待修复]
- L1: AKShare futures_dce_position_rank(date, vars_list=['J']) — 7天回溯
- L2: 无备源（DCE持仓排名仅AKShare提供）
- L3: 无付费源备选
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
- 已知问题: DCE API返回非zip数据，7天回溯可能全部失败
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "J"
FACTOR_CODE = "J_POS_NET"
BOUNDS = (-500000, 500000)

def fetch():
    pub_date, obs_date = get_pit_dates()
    from datetime import timedelta
    for days_back in range(7):
        d = obs_date - timedelta(days=days_back)
        try:
            result = ak.futures_dce_position_rank(date=d.strftime("%Y%m%d"), vars_list=['J'])
            if result is not None and isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, 'shape') and v.shape[0] > 0:
                        df = v
                        vol_col = 'volume' if 'volume' in df.columns else '成交量'
                        net = float(df[vol_col].sum())
                        return net, d
        except Exception as e:
            continue
    raise ValueError("DCE焦炭持仓排名7天回溯全部失败")

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare', source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
