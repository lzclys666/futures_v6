#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取仓单
因子: M_STK_WARRANT = 抓取仓单

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "M_STK_WARRANT"
SYMBOL = "M"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates(freq="日频")
    if obs_date is None:
        print("非交易日，跳过")
        return 0

    print(f"=== {FACTOR_CODE} === obs={obs_date}")
    print("[L1-4] CZCE豆粕(M)无免费仓单数据（厂库交割制度）")
    print("[永久跳过] 建议订阅隆众资讯或Mysteel获取豆粕库存数据")
    print(f"{FACTOR_CODE}: SKIP(无免费源)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
