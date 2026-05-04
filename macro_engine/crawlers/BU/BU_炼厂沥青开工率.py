#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_炼厂沥青开工率.py
因子: BU_BU_STK_REFINE_RATE = 炼厂沥青开工率（%）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: 无免费API（沥青炼厂开工率属商业数据，隆众/卓创年费订阅）
- L2: 无备选源
- L3: save_l4_fallback() 兜底（仅当db有历史值时写入）
- 不写占位符

订阅优先级: ★★★
替代付费源: 隆众资讯(年费) / 卓创资讯(年费)
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

FACTOR_CODE = "BU_BU_STK_REFINE_RATE"
SYMBOL = "BU"


def main():
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); return 0

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1-L2: 无免费数据源
    print("[L1] 无免费API（炼厂开工率属商业数据）")
    print("[L2] 无备选源")

    # L3: save_l4_fallback
    if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(炼厂开工率)"):
        print(f"[SKIP] {FACTOR_CODE} 无免费数据源，不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
