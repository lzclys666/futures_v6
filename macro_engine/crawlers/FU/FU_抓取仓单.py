#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_抓取仓单.py
因子: FU_WARRANT = 上期所燃料油仓单数量（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_shfe_warehouse_receipt（SHFE官网仓单数据）
- L2: SHFE官网直接爬取
- L3: 备用数据源
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak
import requests
import pandas as pd
from datetime import datetime, timedelta

FACTOR_CODE = "FU_WARRANT"
SYMBOL = "FU"


def fetch_shfe_warrant_ak():
    """L1: AKShare futures_shfe_warehouse_receipt"""
    try:
        # 尝试最近5个交易日
        for days_back in range(5):
            check_date = datetime.now() - timedelta(days=days_back)
            date_str = check_date.strftime("%Y%m%d")
            try:
                data = ak.futures_shfe_warehouse_receipt(date=date_str)
                if data is None:
                    continue
                # data可能是dict或DataFrame
                if isinstance(data, dict):
                    # 找FU相关数据
                    for key, val in data.items():
                        if 'FU' in str(key).upper() or '燃料' in str(key):
                            print(f"[L1] SHFE仓单({date_str}): {key}={val}")
                            if val and float(val) > 0:
                                return float(val), date_str
                elif isinstance(data, pd.DataFrame):
                    df_str = data.to_string()
                    # 在DataFrame中找FU行
                    for idx, row in data.iterrows():
                        row_str = str(row.to_string()).upper()
                        if 'FU' in row_str or '燃料' in row_str:
                            # 尝试提取数值
                            for col in data.columns:
                                try:
                                    v = float(str(row[col]).replace(",", ""))
                                    if v > 0:
                                        print(f"[L1] SHFE仓单({date_str}): {v}")
                                        return v, date_str
                                except:
                                    continue
            except Exception as inner_e:
                print(f"[L1] {date_str} 尝试失败: {inner_e}")
                continue
    except Exception as e:
        print(f"[L1] AKShare失败: {e}")
    return None, None


def fetch_shfe_direct():
    """L2: 直接爬取SHFE官网仓单页面"""
    try:
        # SHFE仓单页面
        url = "http://www.shfe.com.cn/data/delay/warehouse_receipt.js"
        r = requests.get(url, timeout=15)
        r.encoding = 'utf-8'
        data = r.json()
        # 格式: {"o": [...]}
        items = data.get("o", [])
        for item in items:
            # item格式: [品种, 仓单数量, 变化]
            if item and len(item) >= 2:
                name = str(item[0]).upper()
                if 'FU' in name or '燃料' in str(item[0]):
                    val = float(str(item[1]).replace(",", ""))
                    date_str = datetime.now().strftime("%Y%m%d")
                    print(f"[L2] SHFE直爬: {name}={val}")
                    return val, date_str
    except Exception as e:
        print(f"[L2] SHFE直爬失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None

    # L1
    val, source = fetch_shfe_warrant_ak()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=1.0, source=f"L1-AKShare-SHFE:{source}")
        return

    # L2
    val, source = fetch_shfe_direct()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.9, source=f"L2-SHFE官网:{source}")
        return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，写入NULL占位")
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位")


if __name__ == "__main__":
    main()
