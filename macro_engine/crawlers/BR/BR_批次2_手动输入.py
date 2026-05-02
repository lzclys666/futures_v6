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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db, get_latest_value

SYMBOL = "BR"

FACTORS = [
    {
        "code": "BR_COST_BD",
        "name": "丁二烯华东现货价",
        "unit": "元/吨",
        "bounds": (4000, 20000),
        "source": "SMM(年费)/隆众资讯(年费)",
        "hint": "SMM或隆众: 丁二烯华东出罐价",
    },
    {
        "code": "BR_COST_ETH",
        "name": "乙烯装置开工率",
        "unit": "%",
        "bounds": (50, 100),
        "source": "隆众资讯(年费)/卓创资讯",
        "hint": "乙烯裂解开工率或MTBE开工率作为代理",
    },
    {
        "code": "BR_COST_MARGIN",
        "name": "丁二烯橡胶毛利",
        "unit": "元/吨",
        "bounds": (-5000, 10000),
        "source": "派生: BR_SPOT_PRICE - BR_COST_BD×0.82 - 3000",
        "hint": "自动计算，来自BR_SPOT_PRICE和BR_COST_BD",
        "auto": True,
    },
    {
        "code": "BR_DEM_TIRE_ALLST",
        "name": "全钢胎开工率",
        "unit": "%",
        "bounds": (30, 100),
        "source": "隆众资讯(年费)",
        "hint": "山东地区全钢胎样本企业开工率",
    },
    {
        "code": "BR_DEM_TIRE_SEMI",
        "name": "半钢胎开工率",
        "unit": "%",
        "bounds": (30, 100),
        "source": "隆众资讯(年费)",
        "hint": "山东地区半钢胎样本企业开工率",
    },
    {
        "code": "BR_DEM_AUTO",
        "name": "中国汽车销量",
        "unit": "万辆/月",
        "bounds": (50, 500),
        "source": "中国汽车工业协会(免费月度发布)",
        "hint": "狭义乘用车批发销量，发布滞后1-2月",
    },
    {
        "code": "BR_SUP_RATE",
        "name": "高顺顺丁橡胶开工率",
        "unit": "%",
        "bounds": (30, 100),
        "source": "隆众资讯(年费)/卓创资讯",
        "hint": "高顺顺丁橡胶样本企业开工率",
    },
]


def calculate_br_margin(pub_date, obs_date):
    """派生计算 BR_COST_MARGIN = 丁二烯橡胶现货价 - 丁二烯成本×0.82 - 3000"""
    br_price = get_latest_value("BR_SPOT_PRICE", SYMBOL)
    bd_cost = get_latest_value("BR_COST_BD", SYMBOL)
    if br_price is None:
        print("  [派生] BR_SPOT_PRICE无数据，无法计算毛利")
        return None
    if bd_cost is None:
        print("  [派生] BR_COST_BD无数据，跳过毛利计算")
        return None
    margin = br_price - bd_cost * 0.82 - 3000
    print(f"  [派生] BR毛利 = {br_price:.0f} - {bd_cost:.0f}×0.82 - 3000 = {margin:.0f}")
    return margin


def main():
    ensure_table()
    import argparse
    from datetime import date

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    today = date.today()
    pub_date = today.isoformat()

    print(f"=" * 56)
    print(f"  BR批次2 — 付费因子手动录入  @ {pub_date}")
    print(f"=" * 56)

    if args.auto:
        print("[AUTO模式] 跳过手动输入，仅计算派生因子\n")
        margin = calculate_br_margin(pub_date, None)
        if margin is not None:
            save_to_db("BR_COST_MARGIN", SYMBOL, pub_date, pub_date, margin,
                       source_confidence=0.9, source="派生(BR_SPOT_PRICE-BD×0.82-3000)")
            print(f"  ✅ BR_COST_MARGIN={margin:.0f} 写入成功\n")
        print("[AUTO模式] 完成（付费因子需手动录入）")
        return 0

    # 交互模式
    written = 0
    for f in FACTORS:
        code = f["code"]
        if f.get("auto"):
            val = calculate_br_margin(pub_date, None)
            if val is not None:
                save_to_db(code, SYMBOL, pub_date, pub_date, val,
                           source_confidence=0.9, source=f["source"])
                print(f"  ✅ {code}={val:.0f} ({f['unit']}) 写入成功\n")
            continue

        print(f"--- {code} ({f['name']}) ---")
        print(f"  单位: {f['unit']}  |  合理范围: {f['bounds']}")
        print(f"  数据源: {f['source']}")
        print(f"  提示: {f['hint']}")

        try:
            val_str = input(f"  输入 {code}（留空跳过）: ").strip()
        except EOFError:
            print("  （非交互环境，跳过）\n")
            continue

        if not val_str:
            print("  跳过\n")
            continue

        try:
            val = float(val_str)
        except ValueError:
            print("  输入无效（需为数字），跳过\n")
            continue

        lo, hi = f["bounds"]
        if not (lo <= val <= hi):
            print(f"  ⚠ 值 {val} 超出合理范围 [{lo}, {hi}]，确认是否正确[Y]: ", end="")
            try:
                confirm = input().strip().upper()
            except EOFError:
                confirm = ""
            if confirm != "Y":
                print("  跳过\n")
                continue

        save_to_db(code, SYMBOL, pub_date, pub_date, val,
                   source_confidence=0.8, source=f["source"])
        print(f"  ✅ {code}={val} ({f['unit']}) 写入成功\n")
        written += 1

    print(f"=" * 56)
    print(f"完成，共写入 {written} 个因子")
    print(f"=" * 56)
    return 0


if __name__ == "__main__":
    exit(main())
