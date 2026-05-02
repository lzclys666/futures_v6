#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取TIPS.py
因子: AG_MACRO_US_TIPS_10Y = 美国10年期TIPS实际收益率（%）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: FRED DFII10（TIPS 10Y 实际收益率）
- L2: FRED DGS10（10Y 名义国债收益率，备用）
- bounds: [-0.5, 5.0]%

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import requests
from datetime import datetime

FACTOR_CODE = "AG_MACRO_US_TIPS_10Y"
SYMBOL = "AG"
# TIPS 10Y 实际收益率合理范围: -0.5% ~ 3.0%
# FRED 返回百分数形式 (1.92 表示 1.92%)
EMIN = -0.5
EMAX = 5.0

def fetch_fred_csv(series_id):
    """从FRED CSV获取最新观测值"""
    today = datetime.now().strftime('%Y-%m-%d')
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&vintage_date={today}'
    try:
        r = requests.get(url, timeout=15)
        lines = r.text.strip().split('\n')
        if len(lines) < 2:
            return None, None
        # 倒序找最新非空值
        for line in reversed(lines[1:]):
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip() not in ('.', ''):
                date_str = parts[0].strip()
                val = float(parts[1].strip())
                return val, datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        print(f"[{series_id}] 获取失败: {e}")
    return None, None

def fetch():
    # L1: DFII10 (10Y TIPS 实际收益率)
    print("[L1] FRED DFII10 (TIPS 10Y 实际收益率)...")
    val, obs = fetch_fred_csv('DFII10')
    if val is not None:
        print(f"[L1] DFII10={val:.4f}% obs={obs}")
        if not (EMIN <= val <= EMAX):
            print(f"[校验失败] DFII10={val:.4f}% 超出合理范围[{EMIN},{EMAX}]")
            val = None
            obs = None

    # L2: DGS10 (10Y 名义国债收益率) - 备用
    if val is None:
        print("[L2] FRED DGS10 (10Y 名义国债收益率) 备用...")
        val2, obs2 = fetch_fred_csv('DGS10')
        if val2 is not None:
            print(f"[L2] DGS10={val2:.4f}% obs={obs2}")
            if EMIN <= val2 <= EMAX:
                val = val2
                obs = obs2

    return val, obs

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val, data_obs = fetch()
    if val is not None:
        # 使用实际数据日期
        write_obs = data_obs if data_obs else obs_date
        conf = 1.0 if data_obs and abs((data_obs - obs_date).days) <= 3 else 0.8
        source = "FRED_DFII10" if conf == 1.0 else "FRED_DGS10_名义"
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, val,
                   source_confidence=conf, source=source)
        print(f"[OK] {FACTOR_CODE}={val:.4f}% ({source}) 写入成功")
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_回补")
            print(f"[OK-L4] {FACTOR_CODE}={v} L4回补")
        else:
            print("[WARN] 无历史数据，跳过")

if __name__ == "__main__":
    main()
