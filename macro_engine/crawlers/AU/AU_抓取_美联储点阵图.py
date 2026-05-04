#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_美联储点阵图（2026年末利率预测中位数）.py
因子: AU_FED_DOT = 美联储点阵图2026年末利率预测中位数（%）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- 数据源: 无免费源。FOMC projections页面404/403。付费订阅: federalreserve.gov FOMC projections
- L3: save_l4_fallback() 兜底（使用历史最新值）

订阅优先级: ★★★★★（付费订阅 federalreserve.gov FOMC projections）
替代付费源: federalreserve.gov FOMC projections
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

FACTOR_CODE = "AU_FED_DOT"
SYMBOL = "AU"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return

    print("[INFO] AU_FED_DOT 无免费数据源（FOMC projections页面404/403）")
    print("[INFO] 付费订阅: federalreserve.gov FOMC projections")
    # L3: 历史回补
    if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(Fed点阵图)"):
        print(f"[WARN] {FACTOR_CODE} DB无历史值，需手动录入（付费订阅: federalreserve.gov）")


if __name__ == "__main__":
    main()
