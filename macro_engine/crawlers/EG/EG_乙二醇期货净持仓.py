#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_抓取_期货净持仓.py
因子: EG_POS_NET = 乙二醇期货净持仓

公式: 多头持仓 - 空头持仓（DCE前20名）

当前状态: [⚠️待修复]
- DCE持仓排名接口需验证
- 备选: AKShare futures_dce_position_rank

订阅优先级: 无（免费源需验证）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

FACTOR_CODE = "EG_POS_NET"
SYMBOL = "EG"

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: DCE持仓排名
    try:
        print("[L1] AKShare futures_dce_position_rank()...")
        # DCE接口需验证，暂不实现
        raise NotImplementedError("DCE接口待验证")
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="乙二醇净持仓")

if __name__ == "__main__":
    run()
