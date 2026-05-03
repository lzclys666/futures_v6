#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_大豆到港量.py
因子: M_BEAN_ARRIVAL = 大豆到港量（万吨，按月/周统计）

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 我的农产品网/天下粮仓大豆到港船期数据需付费订阅
- L1: 我的农产品网公开页面（部分免费）
- L2: 海关总署月度大豆进口数据（免费）
- L3: USDA月度报告（免费）
- L4: DB回补
- L5: NULL占位

订阅优先级: ★★★★（核心供需指标）
替代付费源: 我的农产品网（年费）、天下粮仓（年费）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
from common.web_utils import fetch_url, fetch_json
import re

FACTOR_CODE = "M_BEAN_ARRIVAL"
SYMBOL = "M"


def fetch_arrival_nyjx():
    """L1: 我的农产品网到港数据"""
    url = "https://www.nyjx.com/portal/article/list?category=16&page=1"
    text, err = fetch_url(url, encoding='utf-8', timeout=15)
    if err:
        print(f"[L1] 我的农产品网失败: {err}")
        return None
    try:
        m = re.search(r"到港[^0-9]*?(\d+\.?\d*)\s*万", text)
        if m:
            val = float(m.group(1))
            print(f"[L1] 我的农产品网到港量: {val}万吨")
            return val
    except Exception as e:
        print(f"[L1] 我的农产品网解析失败: {e}")
    return None


def fetch_customs_soybean():
    """L2: 海关总署大豆进口数据（月度，较滞后）"""
    # 海关总署公开数据 - 尝试查询接口
    print("[L2] 海关总署数据接口待验证，跳过")
    return None


def fetch_usda_soybean():
    """L3: USDA PSD数据库CSV"""
    url = "https://apps.fas.usda.gov/psdonline/downloads/psd_al1.csv"
    text, err = fetch_url(url, encoding='utf-8', timeout=20)
    if err:
        print(f"[L3] USDA失败: {err}")
        return None
    try:
        lines = text.splitlines()
        for line in lines:
            if 'China' in line and 'Soybeans' in line:
                parts = line.split(',')
                if len(parts) >= 8:
                    try:
                        val = float(parts[-3])
                        print(f"[L3] USDA中国大豆进口: {val}万吨")
                        return val
                    except (ValueError, IndexError):
                        pass
    except Exception as e:
        print(f"[L3] USDA解析失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val = None

    # L1
    val = fetch_arrival_nyjx()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.8, source="L1-我的农产品网")
        return

    # L2
    val = fetch_customs_soybean()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.9, source="L2-海关总署")
        return

    # L3
    val = fetch_usda_soybean()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.9, source="L3-USDA")
        return

    # L4
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效（付费），写入NULL占位")
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位(付费)")


if __name__ == "__main__":
    main()