#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_全国高速公路整车流量.py
因子: BU_BU_MACRO_HIGHWAY = 全国高速公路整车流量（元）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: 无免费API（交通运输部月度公路货运数据，无公开接口）
- L2: 无备选源
- L3: save_l4_fallback() 兜底（仅当db有历史值时写入）
- 不写占位符

订阅优先级: ★★★
替代付费源: 交通运输部官网 / Mysteel年费（公路货运量）
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

FACTOR_CODE = "BU_BU_MACRO_HIGHWAY"
SYMBOL = "BU"


def main():
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); return 0

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1-L2: 无免费数据源
    print("[L1] 无免费API（交通运输部月度公路货运数据）")
    print("[L2] 无备选源")

    # L3: save_l4_fallback
    if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(高速公路流量)"):
        print(f"[SKIP] {FACTOR_CODE} 无免费数据源，不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
