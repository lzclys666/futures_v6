#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取产量
因子: sa_sup_output_w = 抓取产量

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback, get_latest_value

FACTOR_CODE = "sa_sup_output_w"
SYMBOL = "SA"

def fetch():
    print("[L1] 无免费API（百川盈孚/卓创资讯需订阅），跳过")
    return None

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val = fetch()
    if val is not None:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
