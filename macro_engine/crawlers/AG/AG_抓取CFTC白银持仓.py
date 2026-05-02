#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取CFTC白银持仓.py
因子: AG_POS_CFTC_NET = CFTC白银非商业净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- AKShare macro_usa_cftc_nc_holding 只包含9种货币数据（USD/CHF/NZD/MXN/JPY/EUR/CAD/GBP/AUD）
- AKShare没有免费的CFTC白银持仓数据源
- 不写占位符

订阅优先级: ★★★
替代付费源: CFTC官网（每周五发布）/ Bloomberg Terminal
"""
import sys

FACTOR_CODE = "AG_POS_CFTC_NET"
SYMBOL = "AG"

def main():
    print("[SKIP] AG_POS_CFTC_NET: AKShare无CFTC白银持仓数据（只有货币数据）")
    print("[SKIP] 订阅CFTC官网或Bloomberg获取白银CFTC数据")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
