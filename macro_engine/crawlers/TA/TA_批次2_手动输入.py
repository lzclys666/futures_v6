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
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates

SYMBOL = "TA"
# [WARN]️ 永久跳过因子：auto模式不写数据，不做L4回补
PERMANENT_SKIP_FACTORS = [
    {
        "factor": "TA_CST_PX",
        "name": "PX CFR中国",
        "unit": "美元/吨",
        "source": "隆众资讯/普氏",
        "desc": "对二甲苯CFR中国主港价格",
        "range": (600, 1200),
    },
    {
        "factor": "TA_CST_PROCESSING_FEE",
        "name": "PTA加工费",
        "unit": "元/吨",
        "source": "隆众资讯/普氏",
        "desc": "PTA现货-PX成本",
        "range": (300, 1200),
    },
    {
        "factor": "TA_DEM_POLYESTER_OP",
        "name": "聚酯开工率",
        "unit": "%",
        "source": "隆众资讯/CCF",
        "desc": "聚酯产业链开工率",
        "range": (50, 100),
    },
    {
        "factor": "TA_SUP_OP_RATE",
        "name": "PTA开工率",
        "unit": "%",
        "source": "隆众资讯",
        "desc": "PTA装置开工率",
        "range": (50, 100),
    },
]


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    is_auto = '--auto' in sys.argv

    print(f"=== TA批次2 付费因子 === obs={obs_date} mode={'auto' if is_auto else 'manual'}")

    if is_auto:
        print("[永久跳过] 以下因子无免费数据源，不写占位符，不做L4回补：")
        for f in PERMANENT_SKIP_FACTORS:
            print(f"  -->  {f['factor']:30} {f['name']}（付费: {f['source']}）")
        print("\n订阅隆众资讯/普氏后，使用手动模式录入数据。")
        return 0

    # 手动模式
    print("\n请依次输入各因子值（直接回车跳过）：")
    print("-" * 50)
    for f in PERMANENT_SKIP_FACTORS:
        fc = f["factor"]
        prompt = f"{f['name']}({fc}) [{f['unit']}] 付费:{f['source']} 范围:{f['range']}: "
        val_str = input(prompt).strip()
        if not val_str:
            print(f"  -->  跳过")
            continue
        try:
            val = float(val_str)
            mn, mx = f["range"]
            if not (mn <= val <= mx):
                print(f"  [WARN]  警告: {val} 超出参考范围[{mn},{mx}]，仍写入")
            save_to_db(fc, SYMBOL, pub_date, pub_date, val,
                       source_confidence=0.8, source="手动录入")
            print(f"  [OK] {fc}={val} 写入成功")
        except ValueError:
            print(f"  [FAIL] 无效输入: {val_str}")
    print("\n[完成]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
