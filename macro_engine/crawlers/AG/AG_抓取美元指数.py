#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取美元指数.py
因子: AG_MACRO_DXY = 美元指数（DXY）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- DXY（ICE美元指数）无免费数据源
- FRED CSV端点已需要认证，不再支持无Key访问
- AU_DXY使用FRED DTWEXBGS（广义美元指数）作为替代，但与DXY不同
- 不写占位符

订阅优先级: ★★★
替代付费源: FRED API Key（免费注册）/ Wind / Bloomberg
"""
import sys

FACTOR_CODE = "AG_MACRO_DXY"
SYMBOL = "AG"

def main():
    print("[SKIP] AG_MACRO_DXY: DXY无免费数据源（FRED已需认证）")
    print("[SKIP] 注册FRED API Key（免费）或订阅Wind/Bloomberg获取DXY")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
