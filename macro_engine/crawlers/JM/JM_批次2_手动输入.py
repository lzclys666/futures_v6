#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2_手动输入
因子: 待定义 = 批次2_手动输入

公式: 数据采集（无独立计算公式）

当前状态: [WARN] 待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: [付费]
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db
from datetime import date

SYMBOL = "JM"

FACTORS = [
    # === 批次2: 供给端 ===
    {"code": "JM_SPD_BASIS",        "name": "焦煤期现基差",       "unit": "元/吨", "bounds": (-500, 500),  "source": "[永久跳过] 无可靠免费源",    "skip": True,  "batch": 2},
    {"code": "JM_SUP_CAP",           "name": "煤矿总产能",         "unit": "万吨/年","bounds": (10000, 20000),"source": "Mysteel/汾渭能源(年费)",   "skip": False, "batch": 2},
    {"code": "JM_SUP_CAP_RUN",       "name": "有效产能",           "unit": "万吨/年","bounds": (8000, 18000),"source": "Mysteel/汾渭能源(年费)",   "skip": False, "batch": 2},
    {"code": "JM_SUP_RATE",          "name": "产能利用率",        "unit": "%",    "bounds": (60, 100),    "source": "Mysteel/汾渭能源(年费)",   "skip": False, "batch": 2},
    {"code": "JM_INV_PORT",          "name": "港口库存",           "unit": "万吨",  "bounds": (100, 800),   "source": "Mysteel/汾渭能源(年费)",   "skip": False, "batch": 2},
    {"code": "JM_INV_WAREHOUSE",     "name": "交割库库存",         "unit": "万吨",  "bounds": (0, 50),      "source": "上期所(免费)",            "skip": False, "batch": 2},
    # === 批次3: 需求端 ===
    {"code": "JM_DEM_STEEL",         "name": "钢厂焦煤库存天数",   "unit": "天",   "bounds": (7, 30),      "source": "Mysteel(年费)",            "skip": False, "batch": 3},
    {"code": "JM_DEM_IRON_OUTPUT",  "name": "生铁产量",           "unit": "万吨/月","bounds": (5000, 9000),"source": "国家统计局(免费月度)",     "skip": False, "batch": 3},
    {"code": "JM_DEM_IRON_RATE",    "name": "高炉开工率",         "unit": "%",    "bounds": (50, 100),    "source": "Mysteel(年费)",            "skip": False, "batch": 3},
    {"code": "JM_DEM_POWER",         "name": "电力行业耗煤量",    "unit": "万吨/月","bounds": (1000, 5000),"source": "国家统计局(免费月度)",    "skip": False, "batch": 3},
    # === 批次4: 成本+宏观 ===
    {"code": "JM_COST_TRANS",        "name": "蒙煤到厂成本",       "unit": "元/吨", "bounds": (800, 2000),  "source": "汾渭能源(年费)",            "skip": False, "batch": 4},
    {"code": "JM_COST_FREIGHT",      "name": "蒙煤到港运费",       "unit": "元/吨", "bounds": (100, 500),   "source": "汾渭能源(年费)",            "skip": False, "batch": 4},
    {"code": "JM_MACRO_CHINA_PPI",  "name": "中国PPI同比",        "unit": "%",    "bounds": (-10, 10),    "source": "国家统计局(免费)",          "skip": False, "batch": 4},
    {"code": "JM_MACRO_MANUF_PMI",  "name": "制造业PMI",           "unit": "",     "bounds": (40, 60),     "source": "国家统计局(免费)",          "skip": False, "batch": 4},
]


def main():
    ensure_table()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    today = date.today()
    pub_date = today.isoformat()
    print("=" * 60)
    print(f"  JM批次2/3/4 - 付费因子录入  @ {pub_date}")
    print("=" * 60)
    if args.auto:
        print("[AUTO模式] JM批次2/3/4为付费因子或永久跳过，无免费采集路径")
        print("[AUTO模式] JM_SPD_BASIS已标记永久跳过（无可靠免费源）")
        print("[AUTO模式] 完成")
        return 0
    written = 0
    for f in FACTORS:
        print(f"\n--- {f['code']} ({f['name']}) [批次{f['batch']}] ---")
        print(f"  单位: {f['unit']}  |  合理范围: {f['bounds']}")
        print(f"  数据源: {f['source']}")
        try:
            val_str = input(f"  输入 {f['code']}（留空跳过）: ").strip()
        except EOFError:
            print("  （非交互环境，跳过）")
            continue
        if not val_str:
            print("  跳过")
            continue
        try:
            val = float(val_str)
        except ValueError:
            print("  输入无效（需为数字），跳过")
            continue
        lo, hi = f["bounds"]
        if not (lo <= val <= hi):
            print(f"  [WARN] 值 {val} 超出合理范围 [{lo}, {hi}]，确认[Y]: ", end="")
            try:
                confirm = input().strip().upper()
            except EOFError:
                confirm = ""
            if confirm != "Y":
                print("  跳过")
                continue
        save_to_db(f["code"], SYMBOL, pub_date, pub_date, val,
                   source_confidence=0.8, source=f["source"])
        print(f"  [OK] {f['code']}={val} {f['unit']} 写入成功")
        written += 1
    print(f"\n{'=' * 60}")
    print(f"完成，共写入 {written} 个因子")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    exit(main())
