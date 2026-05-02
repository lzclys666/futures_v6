#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TA_抓取PTA成本.py
因子: TA_CST_PROCESSING_FEE = PTA加工费（元/吨）

公式: PTA加工费 ~= PTA售价 - PX成本(依赖PX CFR)
注: PX CFR属付费数据，此脚本auto模式永久跳过

当前状态: [WARN]️ 永久跳过 -- 无PX免费源，不写占位符
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, get_pit_dates

SYMBOL = "TA"
FACTOR_CODE = "TA_CST_PROCESSING_FEE"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    print("  [跳过] PTA加工费依赖PX CFR价格，无免费数据源")
    print("  [跳过] 订阅隆众资讯/普氏后，手动录入PX价格，再计算加工费")
    print("  [跳过] 不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
