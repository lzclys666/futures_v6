#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算期现基差.py
因子: AL_SPD_BASIS = 沪铝期现基差（元/吨）

公式: 基差 = 沪铝现货价 - 沪铝期货主力价格

当前状态: ⛔永久跳过
- 无免费现货价格数据源
- 上海有色网(SMM)/我的钢铁网(Mysteel)的铝现货报价均需付费订阅
- 无LME/COME等国际现货价免费接口
- 无其他可靠免费源获取铝现货价
- 不写占位符（L4回补仅用于手动录入场景，非正常采集）

订阅优先级: ★★★★
替代付费源: Mysteel年费 | SMM年费（沪铝现货报价）
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "AL_SPD_BASIS"
SYMBOL = "AL"


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("[SKIP] 非交易日"); exit(0)
    print("[SKIP] AL_SPD_BASIS: 无免费铝现货价格数据源（SMM/Mysteel需付费订阅）")
    print("[SKIP] 不写占位符，订阅Mysteel/SMM后手动录入")
