#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_抓取仓单.py
因子: FU_WARRANT = 上期所燃料油仓单数量（吨）

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- L1: AKShare futures_shfe_warehouse_receipt（SHFE官网仓单数据）
- L2: SHFE官网直接爬取
- L3: 备用数据源
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak
from common.web_utils import fetch_json
import pandas as pd
from datetime import datetime, timedelta

FACTOR_CODE = "FU_WARRANT"
SYMBOL = "FU"
BOUNDS = (0, 500000)  # 燃料油仓单 0-50万吨


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
                                except (ValueError, IndexError):
                                    continue
            except Exception as inner_e:
                print(f"[L1] {date_str} 尝试失败: {inner_e}")
                continue
    except Exception as e:
        print(f"[L1] AKShare失败: {e}")
    return None, None


def fetch_shfe_direct():
    """L2: 直接爬取SHFE官网仓单页面"""
    url = "http://www.shfe.com.cn/data/delay/warehouse_receipt.js"
    data, err = fetch_json(url, timeout=15)
    if err:
        print(f"[L2] SHFE直爬失败: {err}")
        return None, None
    try:
        items = data.get("o", [])
        for item in items:
            if item and len(item) >= 2:
                name = str(item[0]).upper()
                if 'FU' in name or '燃料' in str(item[0]):
                    val = float(str(item[1]).replace(",", ""))
                    date_str = datetime.now().strftime("%Y%m%d")
                    print(f"[L2] SHFE直爬: {name}={val}")
                    return val, date_str
    except Exception as e:
        print(f"[L2] SHFE解析失败: {e}")
    return None, None


def fetch_shfe_warrant_get_receipt():
    """L1: AKShare get_receipt（替代已失效的futures_shfe_warehouse_receipt）"""
    try:
        from datetime import datetime, timedelta
        for days_back in range(5):
            check_date = datetime.now() - timedelta(days=days_back)
            if check_date.weekday() >= 5:
                continue
            date_str = check_date.strftime("%Y%m%d")
            try:
                df = ak.get_receipt(start_date=date_str, end_date=date_str, vars_list=["FU"])
                if df is not None and len(df) > 0:
                    row = df.iloc[-1]
                    val = float(row["receipt"])
                    obs_date_raw = str(row["date"])
                    obs_date_fmt = f"{obs_date_raw[:4]}-{obs_date_raw[4:6]}-{obs_date_raw[6:8]}"
                    print(f"[L1] get_receipt({obs_date_fmt}): {val}")
                    return val, obs_date_fmt
            except Exception as inner_e:
                print(f"[L1] {date_str} 失败: {inner_e}")
                continue
    except Exception as e:
        print(f"[L1] get_receipt失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # L1: AKShare get_receipt
    val, obs_dt = fetch_shfe_warrant_get_receipt()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_dt, val,
                    source_confidence=1.0, source=f"AKShare-get_receipt")
        print(f"[OK] {FACTOR_CODE}={val}")
        return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功 (obs={orig_obs_date})")
        return

    print(f"[L5] {FACTOR_CODE}: 无历史数据可回补")


if __name__ == "__main__":
    main()
