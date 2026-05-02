#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取黄金白银比_FRED.py
因子: AG_MACRO_GOLD_SILVER_RATIO = 金银比（已废弃，由AG_抓取黄金白银比.py替代）

公式: 数据采集（无独立计算公式）

当前状态: ⛔已废弃
- 本脚本已废弃，功能与AG_抓取黄金白银比.py完全重复
- AG_抓取黄金白银比.py使用SGE现货数据作为L1源，本脚本只有L4回补
- run_all.py中已由AG_抓取黄金白银比.py覆盖，无需再运行
- 不写占位符

订阅优先级: 无
替代付费源: 无
"""
import sys

FACTOR_CODE = "AG_MACRO_GOLD_SILVER_RATIO"
SYMBOL = "AG"

def main():
    print("[SKIP] AG_抓取黄金白银比_FRED: 已废弃，由AG_抓取黄金白银比.py替代")
    print("[SKIP] run_all.py中已由SGE版本覆盖，无需再运行")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
