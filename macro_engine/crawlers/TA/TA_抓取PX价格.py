#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取PX价格
因子: TA_CST_PX = 抓取PX价格

公式: 数据采集（无独立计算公式）

当前状态: [SKIP]永久跳过
- PX CFR中国无免费数据源（付费:隆众资讯/普氏/卓创资讯）")
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, get_pit_dates

SYMBOL = "TA"
FACTOR_CODE = "TA_CST_PX"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # L1: 无免费数据源
    print("  [跳过] PX CFR中国无免费数据源（付费:隆众资讯/普氏/卓创资讯）")
    print("  [跳过] 订阅付费后从年费账号导出，手动录入本因子")
    print("  [跳过] 不写占位符，不做L4回补（付费数据无意义回补）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
