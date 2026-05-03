#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_油厂开机率.py
因子: M_PLANT_OP_RATE = 油厂大豆压榨开机率（%）

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 我的农产品网（农村农业部）开机率数据需付费订阅
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

FACTOR_CODE = "M_PLANT_OP_RATE"
SYMBOL = "M"


def fetch_plant_op_rate_nyjx():
    """L1: 我的农产品网（nyjx.com）"""
    try:
        url = "https://www.nyjx.com/portal/article/list?category=14&page=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/html",
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        text = r.text
        # 尝试提取开机率数字
        m = re.search(r"开机率[^0-9]*?(\d+\.?\d*)\s*%", text)
        if m:
            val = float(m.group(1))
            print(f"[L1] 我的农产品网开机率: {val}%")
            return val
    except Exception as e:
        print(f"[L1] 我的农产品网失败: {e}")
    return None


def fetch_plant_op_rate_agri():
    """L3: 农业农村部官网周度数据"""
    try:
        url = "http://www.agri.cn/zxgz/yzgnyx/2026/t20260415_"
        # 农业农村部不定期发布油厂开机数据
        # 尝试访问大豆压榨相关页面
        pass
    except Exception as e:
        print(f"[L3] 农业农村部失败: {e}")
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

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效（付费数据），写入NULL占位")
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位(付费)")


if __name__ == "__main__":
    main()
