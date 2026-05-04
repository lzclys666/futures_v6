#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_SHFE沪金前20会员净持仓.py
因子: AU_SHFE_OI_RANK = SHFE沪金前20会员净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- 数据源: 无免费源。SHFE官网数据接口404，AKShare DCE不支持SHFE。付费订阅: SHFE官网
- L3: save_l4_fallback() 兜底（使用历史最新值）

订阅优先级: ★★★★★（付费订阅 SHFE官网数据）
替代付费源: SHFE官网数据
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

FACTOR_CODE = "AU_SHFE_OI_RANK"
SYMBOL = "AU"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return

    print("[INFO] AU_SHFE_OI_RANK 无免费数据源（SHFE官网接口404，AKShare不支持SHFE）")
    print("[INFO] 付费订阅: SHFE官网数据")
    # L3: 历史回补
    if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(SHFE沪金前20净持仓)"):
        print(f"[WARN] {FACTOR_CODE} DB无历史值，需手动录入（付费订阅: SHFE官网）")


if __name__ == "__main__":
    main()
