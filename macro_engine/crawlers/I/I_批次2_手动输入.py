#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_批次2_手动输入.py
因子: 11个付费因子（详见PAID_FACTORS）

当前状态: [⛔永久跳过]
- 无免费数据源（付费订阅: Mysteel/SMM/隆众）
- 不写占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

PAID_FACTORS = {
    "I_SUP_OUTPUT":     "铁矿石产量 (Mysteel月频)",
    "I_SUP_SHIPMENT":   "铁矿石发货量 (Mysteel周频)",
    "I_STK_BONDED":     "铁矿石保税区库存 (SMM)",
    "I_DEM_STEEL":      "钢厂铁矿石日耗 (Mysteel日频)",
    "I_DEM_STEEL_MI":   "钢厂铁水产量 (Mysteel日频)",
    "I_COST_BREAKEVEN": "钢厂铁矿石保本价 (Mysteel)",
    "I_COST_PORT":      "铁矿石港口现货价 (Mysteel)",
    "I_OP_RATE":        "矿山开工率 (SMM)",
    "I_CAP_UTIL":       "港口产能利用率 (隆众)",
    "I_SPD_62_65":      "62%-65%品位价差 (SMM)",
    "I_FREIGHT_BDI":    "波罗的海干散货指数BDI",
    "I_POS_NET":        "铁矿石持仓净多 (DCE排名，接口不稳定)",
}

def main():
    print("=" * 60)
    print("[跳过] I批次2因子 - 付费/无免费数据源")
    print("=" * 60)
    for code, desc in PAID_FACTORS.items():
        print(f"  {code}: {desc}")

if __name__ == "__main__":
    main()
