#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_计算近远月价差.py
因子: P_SPD_CONTRACT = 棕榈油近远月价差（元/吨）

公式: P_SPD_CONTRACT = 近月合约价 - 远月合约价

当前状态: ⛔永久跳过
- AKShare futures_spot_price(vars_list=['P']) 只返回到2024-04-30的历史数据，无当前数据
- 无其他可靠免费源获取棕榈油近远月价差
- 不写占位符

订阅优先级: ★★★
替代付费源: MPOB官方月报 | SMM年费（棕榈油期货月间价差）
"""
import sys

FACTOR_CODE = "P_SPD_CONTRACT"
SYMBOL = "P"

def main():
    print("[SKIP] P_SPD_CONTRACT: AKShare只返回到2024-04-30的历史数据，无当前免费源")
    print("[SKIP] 订阅MPOB月报/SMM后，手动录入棕榈油近远月价差")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
