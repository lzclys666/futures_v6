#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2_手动输入
因子: 待定义 = 批次2_手动输入

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
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
    "CU_SUP_OUTPUT":      "精铜产量 (SMM月频)",
    "CU_SUP_IMPORT":      "铜进口量 (海关总署月频)",
    "CU_WRT_LME":         "LME铜仓单/注册仓单 (LME官网，免费但需解析)",
    # 需求侧
    "CU_DEM_WIRE":        "铜杆开工率 (Mysteel)",
    "CU_DEM_TUBE":        "铜管开工率 (Mysteel)",
    "CU_DEM_SHEET":       "铜板带开工率 (Mysteel)",
    # 成本
    "CU_COST_TC":         "铜精矿TC/RC (SMM周频)",
    "CU_COST_IMPORT":     "铜进口盈亏 (LME3月+CIF+汇率，需人工计算)",
    # 宏观
    "CU_FX_LME_CU":       "LME3月铜价USD (LME官网，免费但需解析)",
    "CU_FX_USDCNY":       "美元兑人民币汇率 (BOC中行，免费，已通过currency_boc_safe实现)",
    # 其他
    "CU_OP_RATE":         "冶炼厂开工率 (SMM)",
    "CU_INV_TOTAL":       "三大交易所铜总库存 (SHFE+LME+COMEX，需合并)",
    "CU_SPD_AL_CU":       "铜铝价比 (AL/CU跨品种比价，沪铜/沪铝)",
    "CU_POS_CONCENTRATION":"沪铜持仓集中度 (SHFE)",
}

def print_skip_notice():
    print("=" * 60)
    print("CU批次2因子 - 付费/无免费数据源，auto模式跳过")
    print("=" * 60)
    for code, desc in PAID_FACTORS.items():
        print(f"  {code}: {desc}")
    print()
    print("如需录入数据，请手动修改脚本中的因子值并注释掉return语句")
    print("或使用 py CU_批次2_手动输入.py --manual 交互输入")

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

    print_skip_notice()

if __name__ == "__main__":
    main()
