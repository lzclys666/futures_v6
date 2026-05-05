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

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback

FACTOR_CODE_BATCH2 = [
    ("RB_SUPPLY_STEEL_OUTPUT", "钢厂螺纹钢产量(万吨)", "db_回补"),
    ("RB_DEMAND_REAL_ESTATE", "房地产新开工面积(万平方米)", "db_回补"),
    ("RB_DEMAND_INFRA", "基建投资增速(%)", "db_回补"),
    ("RB_COST_IRON_ORE", "铁矿石到岸价(美元/吨)", "db_回补"),
    ("RB_COST_COKE", "焦炭到厂价(元/吨)", "db_回补"),
]

def manual_input_factors():
    is_auto = "--auto" in sys.argv
    
    if is_auto:
        print("[自动模式] 批次2因子无免费数据源，DB回补...")
        for factor, name, src in FACTOR_CODE_BATCH2:
            save_l4_fallback(factor, "RB", pub_date, obs_date)
        return []
    else:
        print("\n" + "=" * 50)
        print("手动输入模式 - RB批次2因子")
        print("=" * 50)
        print("数据来源: Mysteel我的钢铁网 / 统计局 / Wind")
        print("输入 0 跳过该因子\n")
        results = []
        for factor, name, src in FACTOR_CODE_BATCH2:
            try:
                val_str = input(f"{factor}({name}): ").strip()
                if val_str and val_str != "0":
                    val = float(val_str)
                    results.append((factor, val, '手动输入', 0.6))
                    print(f"  已录入: {factor}={val}")
            except (ValueError, EOFError):
                print(f"  跳过: {factor}")
        return results

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== RB批次2手动输入 @ pub={pub_date} obs={obs_date} ===")
    
    results = manual_input_factors()
    saved = 0
    for factor, value, source, confidence in results:
        save_to_db(factor, "RB", pub_date, obs_date, value, source_confidence=confidence, source=source)
        saved += 1
    
    print(f"\n完成: 写入{saved}条")
