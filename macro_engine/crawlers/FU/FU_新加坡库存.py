#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_新加坡库存.py
因子: FU_SG_INVENTORY = 新加坡燃料油库存（立方米）

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- L1: 新加坡海事港务局（MPA）官网公开数据
- L2: EIA新加坡燃料油库存
- L3: 备用
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 隆众资讯（年费）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
from common.web_utils import fetch_url, fetch_json
import re
from datetime import datetime

FACTOR_CODE = "FU_SG_INVENTORY"
SYMBOL = "FU"
BOUNDS = (500000, 8000000)  # 新加坡燃料油库存 50万-800万立方米


def fetch_sg_inventory_mpa():
    """L1: 新加坡海事港务局（MPA）官网"""
    url = "https://www.mpa.gov.sg/our-business/industry-information/fuel-oil"
    text, err = fetch_url(url, encoding='utf-8', timeout=20)
    if err:
        print(f"[L1] MPA失败: {err}")
        return None, None
    try:
        patterns = [
            r"fuel oil[^<]*?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:million|m³|cubic)",
            r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s*(?:million|m³|cubic).*?fuel",
            r"total[^<]*?fuel[^<]*?(\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val_str = m.group(1).replace(",", "")
                val = float(val_str)
                if val < 10000:
                    val = val * 1000
                date_str = datetime.now().strftime("%Y-%m-%d")
                print(f"[L1] MPA新加坡库存: {val} m³")
                return val, date_str
    except Exception as e:
        print(f"[L1] MPA解析失败: {e}")
    return None, None


def fetch_sg_inventory_eia():
    """L2: EIA新加坡燃料油库存"""
    url = ("https://api.eia.gov/v2/petroleum/pri/snf/data/"
           "?api_key=DEMO_KEY&frequency=weekly&data[0]=value"
           "&facets[process][]=KSTK&sort[0][column]=period"
           "&sort[0][direction]=desc&length=2")
    data, err = fetch_json(url, timeout=15)
    if err:
        print(f"[L2] EIA失败: {err}")
        return None, None
    try:
        rows = data.get("response", {}).get("data", [])
        if rows:
            val = float(rows[0]["value"])
            date_str = rows[0]["period"][:10]
            print(f"[L2] EIA新加坡库存: {date_str} -> {val}")
            return val, date_str
    except Exception as e:
        print(f"[L2] EIA解析失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None

    # L1
    val, source = fetch_sg_inventory_mpa()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                        source_confidence=1.0, source=f"L1-MPA新加坡:{source}")
            return

    # L2
    val, source = fetch_sg_inventory_eia()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                        source_confidence=0.9, source=f"L2-EIA:{source}")
            return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，不写占位符")


if __name__ == "__main__":
    main()