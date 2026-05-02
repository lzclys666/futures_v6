#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货仓单.py
因子: BU_BU_STK_WARRANT = 沥青期货仓单（万吨）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- 数据源: AKShare futures_shfe_warehouse_receipt() → JSON解析失败（网站改版）
- 尝试过的数据源及结果: SHFE仓单API返回非JSON响应（网站改版）
- 解决方案: 无免费源，需订阅上期所数据或Wind

订阅优先级: ★★★
替代付费源: 上期所官网 / Wind / 隆众资讯
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "BU_BU_STK_WARRANT"
SYMBOL = "BU"


def main():
    print("[SKIP] SHFE仓单API失效（JSON解析错误，网站改版）")
    print("[SKIP] 无免费数据源，需付费订阅上期所/Wind")
    print("[SKIP] 不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
