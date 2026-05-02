#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取现货和基差
因子: NR_SPD_BASIS = 抓取现货和基差

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
from datetime import date

FACTOR_CODE = "NR_SPD_BASIS"
SYMBOL = "NR"

def main():
    print("[SKIP] NR_SPD_BASIS: AKShare无NR(20号胶)现货价格")
    latest = get_latest_value(FACTOR_CODE, SYMBOL)
    if latest is not None:
        print("[L4FB] %s=%.0f" % (FACTOR_CODE, latest))
    else:
        print("[SKIP] NR_SPD_BASIS: no data")

if __name__ == "__main__":
    main()
