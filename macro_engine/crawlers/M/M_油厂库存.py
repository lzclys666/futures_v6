#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_油厂库存.py
因子: M_OIL_BEAN_STOCK = 油厂大豆原料库存（万吨）
     M_OIL_MEAL_STOCK = 油厂豆粕库存（万吨）

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: 我的农产品网(nyjx.com)公开页面 — 需网页解析，稳定性待验证
- L2: 天下粮仓（付费）
- L3: 农业农村部周度数据（部分公开）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

订阅优先级: ★★★★★（行业核心指标）
替代付费源: 我的农产品网（年费）、天下粮仓（年费）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
from common.web_utils import fetch_url
import re

FACTOR_CODE_BEAN = "M_OIL_BEAN_STOCK"
FACTOR_CODE_MEAL = "M_OIL_MEAL_STOCK"
SYMBOL = "M"


def fetch_oil_stock_nyjx():
    """L1: 我的农产品网油厂库存"""
    url = "https://www.nyjx.com/portal/article/list?category=15&page=1"
    text, err = fetch_url(url, encoding='utf-8', timeout=15)
    if err:
        print(f"[L1] 我的农产品网失败: {err}")
        return None, None
    try:
        bean_m = re.search(r"大豆.{0,5}库存[^0-9]*?(\d+\.?\d*)\s*万", text)
        meal_m = re.search(r"豆粕.{0,5}库存[^0-9]*?(\d+\.?\d*)\s*万", text)
        bean_val = float(bean_m.group(1)) if bean_m else None
        meal_val = float(meal_m.group(1)) if meal_m else None
        if bean_val:
            print(f"[L1] 油厂大豆库存: {bean_val}万吨")
        if meal_val:
            print(f"[L1] 油厂豆粕库存: {meal_val}万吨")
    except Exception as e:
        print(f"[L1] 我的农产品网解析失败: {e}")
        bean_val, meal_val = None, None
    return bean_val, meal_val


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE_BEAN} & {FACTOR_CODE_MEAL} === pub={pub_date} obs={obs_date}")

    bean_val, meal_val = fetch_oil_stock_nyjx()

    # 大豆库存
    if bean_val is not None:
        save_to_db(FACTOR_CODE_BEAN, SYMBOL, pub_date, obs_date, bean_val,
                    source_confidence=0.8, source="L1-我的农产品网")
        print(f"[OK] {FACTOR_CODE_BEAN}={bean_val}")
    else:
        save_l4_fallback(FACTOR_CODE_BEAN, SYMBOL, pub_date, obs_date)

    # 豆粕库存
    if meal_val is not None:
        save_to_db(FACTOR_CODE_MEAL, SYMBOL, pub_date, obs_date, meal_val,
                    source_confidence=0.8, source="L1-我的农产品网")
        print(f"[OK] {FACTOR_CODE_MEAL}={meal_val}")
    else:
        save_l4_fallback(FACTOR_CODE_MEAL, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
