#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_抓取_批次2手动输入.py
因子: 多个付费因子（批次2）

当前状态: [⛔永久跳过]
- 全部为付费数据源，auto模式跳过
- 手动模式: py CU_抓取_批次2手动输入.py --manual

订阅优先级: ★★★（Mysteel年费/SMM年费）
替代付费源: Wind/Bloomberg
"""
import sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates

PAID_FACTORS = {
    "CU_SUP_OUTPUT":      "精铜产量 (SMM月频)",
    "CU_SUP_IMPORT":      "铜进口量 (海关总署月频)",
    "CU_WRT_LME":         "LME铜仓单/注册仓单 (LME官网，免费但需解析)",
    "CU_DEM_WIRE":        "铜杆开工率 (Mysteel)",
    "CU_DEM_TUBE":        "铜管开工率 (Mysteel)",
    "CU_DEM_SHEET":       "铜板带开工率 (Mysteel)",
    "CU_COST_TC":         "铜精矿TC/RC (SMM周频)",
    "CU_COST_IMPORT":     "铜进口盈亏 (LME3月+CIF+汇率，需人工计算)",
    "CU_FX_LME_CU":       "LME3月铜价USD (LME官网，免费但需解析)",
    "CU_FX_USDCNY":       "美元兑人民币汇率 (BOC中行，免费，已通过currency_boc_safe实现)",
    "CU_OP_RATE":         "冶炼厂开工率 (SMM)",
    "CU_INV_TOTAL":       "三大交易所铜总库存 (SHFE+LME+COMEX，需合并)",
    "CU_SPD_AL_CU":       "铜铝价比 (AL/CU跨品种比价，沪铜/沪铝)",
    "CU_POS_CONCENTRATION":"沪铜持仓集中度 (SHFE)",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    if args.manual:
        print("手动录入模式:")
        for code, desc in PAID_FACTORS.items():
            print(f"  {code}: {desc}")
        return

    # auto模式: 打印跳过信息
    print("=" * 60)
    print("CU批次2因子 - 付费/无免费数据源，auto模式跳过")
    print("=" * 60)
    for code, desc in PAID_FACTORS.items():
        print(f"  [跳过] {code}: {desc}")
    print(f"\n如需录入，请使用 --manual 模式")

if __name__ == "__main__":
    main()
