#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_全国高速公路整车流量.py
因子: BU_BU_MACRO_HIGHWAY = 全国高速公路整车流量（元）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- 数据源：交通运输部月度公路货运数据
- 问题：无免费API，需手动从交通运输部网站下载
- 历史数据：仅2021年前有少量CSV存档，之后无更新
- 不写占位符

订阅优先级: ★★★
替代付费源: 交通运输部官网 | Mysteel年费（公路货运量）
"""
import sys
from pathlib import Path

def main():
    print('[跳过] 交通运输部月度公路货运数据无免费接口')
    print('[跳过] 需手动从交通运输部网站下载或订阅Mysteel')
    print('[跳过] 不写占位符')
    return 0

if __name__ == '__main__':
    sys.exit(main())
