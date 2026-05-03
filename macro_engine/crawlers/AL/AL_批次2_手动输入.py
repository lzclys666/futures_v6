#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_批次2_手动输入.py
因子: AL批次2/3/4 = 铝产业链付费因子（14个）

公式: 各因子独立（见下方因子列表）

当前状态: [OK]手动录入（auto模式跳过，需人工输入）
- 批次2: 氧化铝价格/电解铝产能/开工率/出口量/铝棒库存（付费）
- 批次3: 电力成本/预焙阳极/氟化铝/冰晶石（付费）
- 批次4: 社会库存/工业增加值/交割库/美元指数/PMI（部分免费）

订阅优先级: ★★~★★★★（见下方各因子）
替代付费源: Mysteel年费 | SMM年费
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_latest_value
from datetime import date

SYMBOL = "AL"

# 因子配置（批次2/3/4付费因子）
FACTORS = [
    # === 批次2: 氧化铝 + 电解铝 ===
    {"code": "AL_SPD_AL_OXIDE",     "name": "氧化铝价格",        "unit": "元/吨",  "bounds": (2000, 5000),  "source": "Mysteel/SMM(年费)",      "batch": 2},
    {"code": "AL_SUP_CAP_AL",       "name": "电解铝产能",        "unit": "万吨",   "bounds": (4000, 5000),  "source": "Mysteel/SMM(年费)",      "batch": 2},
    {"code": "AL_SUP_CAP_RUN",      "name": "电解铝运行产能",    "unit": "万吨",   "bounds": (3500, 4800),  "source": "Mysteel/SMM(年费)",      "batch": 2},
    {"code": "AL_SUP_OP_RATE",      "name": "电解铝开工率",      "unit": "%",     "bounds": (60, 100),     "source": "Mysteel/SMM(年费)",      "batch": 2},
    {"code": "AL_EXP_ALUMINUM",    "name": "铝材出口量",        "unit": "万吨/月","bounds": (20, 80),      "source": "海关总署(免费月度)",     "batch": 2},
    {"code": "AL_INV_ALUMINUM_ROD", "name": "铝棒库存",          "unit": "万吨",  "bounds": (5, 50),       "source": "Mysteel/SMM(年费)",      "batch": 2},
    # === 批次3: 成本端 ===
    {"code": "AL_COST_POWER",       "name": "电解铝电力成本",   "unit": "元/吨",  "bounds": (2000, 8000),  "source": "Mysteel/铝厂调研",        "batch": 3},
    {"code": "AL_COST_ANODE",       "name": "预焙阳极成本",     "unit": "元/吨",  "bounds": (3000, 6000),  "source": "Mysteel/SMM(年费)",      "batch": 3},
    {"code": "AL_COST_ALFLUORIDE", "name": "氟化铝价格",        "unit": "元/吨",  "bounds": (8000, 20000), "source": "Mysteel/SMM(年费)",      "batch": 3},
    {"code": "AL_COST_CRYOLITE",    "name": "冰晶石价格",       "unit": "元/吨",  "bounds": (10000, 30000),"source": "Mysteel/SMM(年费)",      "batch": 3},
    # === 批次4: 库存/需求/宏观 ===
    {"code": "AL_INV_SOCIAL",       "name": "电解铝社会库存",   "unit": "万吨",   "bounds": (20, 150),     "source": "Mysteel/SMM(年费)",      "batch": 4},
    {"code": "AL_DEM_POWER",        "name": "工业增加值/用电量","unit": "%",      "bounds": (-10, 20),     "source": "国家统计局(免费月度)",    "batch": 4},
    {"code": "AL_INV_WAREHOUSE",    "name": "交割库库存",       "unit": "万吨",   "bounds": (0, 20),       "source": "上期所(免费)",           "batch": 4},
    {"code": "AL_MACRO_USD_INDEX", "name": "美元指数",          "unit": "",      "bounds": (80, 120),     "source": "FRED美联储(免费)",       "batch": 4},
    {"code": "AL_MACRO_CHINA_PMI", "name": "中国官方PMI",       "unit": "",      "bounds": (40, 60),      "source": "国家统计局(免费月度)",    "batch": 4},
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
    print(f"  AL批次2/3/4 — 付费因子录入  @ {pub_date}")
    print("=" * 60)

    if args.auto:
        print("[AUTO] 付费因子无免费采集路径，请登录Mysteel/SMM手动录入")
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
                   source=f["source"], source_confidence=0.7)
        print(f"  [OK] {f['code']}={val} {f['unit']}")
        written += 1

    print(f"\n{'=' * 60}")
    print(f"完成，共写入 {written} 个因子")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    exit(main())
