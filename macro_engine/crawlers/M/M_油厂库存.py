#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_油厂库存.py
因子: M_OIL_STOCK = 油厂大豆原料库存（万吨）+ 豆粕库存（万吨）

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 我的农产品网/天下粮仓大豆+豆粕库存数据需付费订阅
- L1: 我的农产品网公开页面（部分免费）
- L2: 天下粮仓（付费）
- L3: 农业农村部周度数据（部分公开）
- L4: DB回补
- L5: NULL占位

订阅优先级: ★★★★★（行业核心指标）
替代付费源: 我的农产品网（年费）、天下粮仓（年费）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import requests
import re

FACTOR_CODE_BEAN = "M_OIL_BEAN_STOCK"
FACTOR_CODE_MEAL = "M_OIL_MEAL_STOCK"
SYMBOL = "M"


def fetch_oil_stock_nyjx():
    """L1: 我的农产品网油厂库存"""
    try:
        url = "https://www.nyjx.com/portal/article/list?category=15&page=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        text = r.text
        # 尝试提取库存数字（万吨）
        bean_m = re.search(r"大豆.{0,5}库存[^0-9]*?(\d+\.?\d*)\s*万", text)
        meal_m = re.search(r"豆粕.{0,5}库存[^0-9]*?(\d+\.?\d*)\s*万", text)
        bean_val = float(bean_m.group(1)) if bean_m else None
        meal_val = float(meal_m.group(1)) if meal_m else None
        if bean_val:
            print(f"[L1] 油厂大豆库存: {bean_val}万吨")
        if meal_val:
            print(f"[L1] 油厂豆粕库存: {meal_val}万吨")
        return bean_val, meal_val
    except Exception as e:
        print(f"[L1] 我的农产品网失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE_BEAN} & {FACTOR_CODE_MEAL} === obs={obs_date}")

    bean_val, meal_val = None, None

    # L1
    bean_val, meal_val = fetch_oil_stock_nyjx()

    if bean_val is not None:
        save_to_db(FACTOR_CODE_BEAN, SYMBOL, pub_date, obs_date, bean_val,
                    source_confidence=0.8, source="L1-我的农产品网")
    else:
        # L4: DB fallback
        record = _get_latest_record(FACTOR_CODE_BEAN, SYMBOL)
        if record:
            raw_value, orig_obs_date, orig_source, orig_conf = record
            save_to_db(FACTOR_CODE_BEAN, SYMBOL, pub_date, obs_date, raw_value,
                        source_confidence=0.5, source=f"L4回补({orig_source})")
            print(f"[L4] {FACTOR_CODE_BEAN}={raw_value} 回补成功")
        else:
            save_to_db(FACTOR_CODE_BEAN, SYMBOL, pub_date, obs_date, None,
                        source_confidence=0.0, source="L5-NULL占位(付费)")

    if meal_val is not None:
        save_to_db(FACTOR_CODE_MEAL, SYMBOL, pub_date, obs_date, meal_val,
                    source_confidence=0.8, source="L1-我的农产品网")
    else:
        # L4: DB fallback
        record = _get_latest_record(FACTOR_CODE_MEAL, SYMBOL)
        if record:
            raw_value, orig_obs_date, orig_source, orig_conf = record
            save_to_db(FACTOR_CODE_MEAL, SYMBOL, pub_date, obs_date, raw_value,
                        source_confidence=0.5, source=f"L4回补({orig_source})")
            print(f"[L4] {FACTOR_CODE_MEAL}={raw_value} 回补成功")
        else:
            save_to_db(FACTOR_CODE_MEAL, SYMBOL, pub_date, obs_date, None,
                        source_confidence=0.0, source="L5-NULL占位(付费)")


if __name__ == "__main__":
    main()
