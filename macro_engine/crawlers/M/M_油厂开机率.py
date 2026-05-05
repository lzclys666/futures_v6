#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_油厂开机率.py
因子: M_PLANT_OP_RATE = 油厂大豆压榨开机率（%）

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 我的农产品网开机率数据需付费订阅
- L1: 我的农产品网公开页面（部分免费）
- L2: 天下粮仓（付费）
- L3: 农业农村部周度数据（部分公开）
- L4: DB回补
- L5: NULL占位

订阅优先级: ★★★★★（行业核心指标）
替代付费源: 我的农产品网（年费）、天下粮仓（年费）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
from common.web_utils import fetch_url
import re

FACTOR_CODE = "M_PLANT_OP_RATE"
SYMBOL = "M"


def fetch_plant_op_rate_nyjx():
    """L1: 我的农产品网（nyjx.com）"""
    url = "https://www.nyjx.com/portal/article/list?category=14&page=1"
    text, err = fetch_url(url, encoding='utf-8', timeout=15)
    if err:
        print(f"[L1] 我的农产品网失败: {err}")
        return None
    try:
        m = re.search(r"开机率[^0-9]*?(\d+\.?\d*)\s*%", text)
        if m:
            val = float(m.group(1))
            print(f"[L1] 我的农产品网开机率: {val}%")
            return val
    except Exception as e:
        print(f"[L1] 我的农产品网解析失败: {e}")
    return None


def fetch_plant_op_rate_agri():
    """L3: 农业农村部官网周度数据（URL待验证）"""
    print("[L3] 农业农村部数据URL待验证，跳过")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # L1
    val = fetch_plant_op_rate_nyjx()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.8, source="L1-我的农产品网")
        return

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()