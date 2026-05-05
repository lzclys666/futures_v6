#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取聚酯开工率
因子: TA_DEM_POLYESTER_OP = 抓取聚酯开工率

公式: 数据采集（无独立计算公式）

当前状态: [SKIP]永久跳过
- 聚酯开工率无免费API（付费:隆众资讯/CCF资讯）")
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "TA_DEM_POLYESTER_OP"
SYMBOL = "TA"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    print("  [跳过] 聚酯开工率无免费API（付费:隆众资讯/CCF资讯）")
    print("  [跳过] 不写占位符，订阅付费后手动录入")
    return 0


if __name__ == "__main__":
    sys.exit(main())
