#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_计算期现基差.py
因子: AG_SPD_BASIS = 沪银期现基差（元/千克）

公式: AG_SPD_BASIS = 沪银现货价(元/千克) - AG0主力期货结算价(元/千克)

当前状态: ⚠️ 永久跳过
  - AKShare futures_spot_price 对"沪银"品种返回历史数据（2016年），无当前可用数据
  - AKShare futures_zh_spot 接口故障（Sina数据格式变更）
  - 无其他可靠免费源
  - 订阅隆众资讯/上海有色网后，从年费账号导出沪银现货价数据，手动录入

订阅优先级: ★★★（高）
替代付费源: Mysteel年费 | SMM年费 | 隆众资讯年费
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "AG_SPD_BASIS"
SYMBOL = "AG"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    print("  [跳过] 无免费数据源: futures_zh_spot已崩、futures_spot_price仅返回2016年历史数据")
    print("  [跳过] 订阅Mysteel/SMM/隆众资讯后，手动录入沪银现货价，再计算期现基差")
    print("  [跳过] 不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
