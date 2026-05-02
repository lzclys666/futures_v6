#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_炼厂沥青开工率.py
因子: BU_BU_STK_REFINE_RATE = 炼厂沥青开工率（%）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- 数据源: 无免费API（沥青炼厂开工率属商业数据）
- 尝试过的数据源: 无有效免费源
- 解决方案: 订阅隆众资讯/卓创资讯沥青开工率数据

订阅优先级: ★★★
替代付费源: 隆众资讯(年费) / 卓创资讯(年费)
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import get_pit_dates, get_latest_value

FACTOR_CODE = "BU_BU_STK_REFINE_RATE"
SYMBOL = "BU"


def main():
    print("[SKIP] 炼厂沥青开工率无免费数据源")
    print("[SKIP] 需订阅隆众资讯或卓创资讯")
    print("[SKIP] 不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
