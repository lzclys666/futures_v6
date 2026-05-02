#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2_手动输入
因子: 待定义 = 批次2_手动输入

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_latest_value
from datetime import date

PAID_FACTORS = {
    # 供给侧
    "I_SUP_OUTPUT":    "铁矿石产量 (Mysteel月频)",
    "I_SUP_SHIPMENT":  "铁矿石发货量 (Mysteel周频)",
    "I_STK_BONDED":    "铁矿石保税区库存 (SMM)",
    # 需求侧
    "I_DEM_STEEL":     "钢厂铁矿石日耗 (Mysteel日频)",
    "I_DEM_STEEL_MI":  "钢厂铁水产量 (Mysteel日频，百万吨)",
    # 成本
    "I_COST_BREAKEVEN":"钢厂铁矿石保本价 (Mysteel)",
    "I_COST_PORT":     "铁矿石港口现货价 (Mysteel/我的钢铁)",
    # 开工率/产能
    "I_OP_RATE":       "矿山开工率 (SMM)",
    "I_CAP_UTIL":      "港口产能利用率 (隆众)",
    # 其他
    "I_SPD_62_65":     "62%-65%品位价差 (SMM)",
    "I_FREIGHT_BDI":   "波罗的海干散货指数BDI (免费)",
    "I_POS_NET":       "铁矿石持仓净多 (DCE排名，接口不稳定)",
}

def print_skip_notice():
    print("=" * 60)
    print("I批次2因子 - 付费/无免费数据源，auto模式跳过")
    print("=" * 60)
    for code, desc in PAID_FACTORS.items():
        print(f"  {code}: {desc}")
    print()
    print("如需录入数据，请手动修改脚本中的因子值并注释掉return语句")
    print("或使用 py I_批次2_手动输入.py --manual 交互输入")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()

    if args.auto:
        print_skip_notice()
        return

    if args.manual:
        print("手动录入模式 (示例):")
        for code, desc in PAID_FACTORS.items():
            print(f"  {code}: {desc}")
        return

    # 无参数：打印说明
    print_skip_notice()

if __name__ == "__main__":
    main()
