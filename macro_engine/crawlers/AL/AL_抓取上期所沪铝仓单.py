#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取上期所沪铝仓单.py
因子: AL_INV_SHFE = 上期所沪铝仓单（吨）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- AKShare futures_shfe_warehouse_receipt() 接口仍可访问，但返回数据中AL列检测失败
- SHFE官网所有数据接口返回404（网站已改版）
- 无其他可靠免费源获取SHFE沪铝仓单数据
- 不写占位符

订阅优先级: ★★★★
替代付费源: Mysteel年费 | SMM年费（上期所铝仓单数据）
"""
import sys

FACTOR_CODE = "AL_INV_SHFE"
SYMBOL = "AL"

def main():
    print("[SKIP] AL_INV_SHFE: AKShare SHFE仓单接口AL列检测失败，SHFE官网404，无免费源")
    print("[SKIP] 订阅Mysteel/SMM后，手动录入上期所沪铝仓单数据")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
