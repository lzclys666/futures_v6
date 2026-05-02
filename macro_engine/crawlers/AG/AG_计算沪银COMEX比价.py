#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_计算沪银COMEX比价.py
因子: AG_SPD_SHFE_COMEX = 沪银/COMEX银比价

公式: AG_SPD_SHFE_COMEX = SHFE_AG0收盘价(元/kg) ÷ COMEX_SI0收盘价(元/kg)
    = SHFE_AG0 ÷ (COMEX_SI0_cents_per_oz × 汇率 × 0.321507)

当前状态: ✅正常
- 数据源: 新浪期货AG0 + 新浪期货SI0 + 新浪USDCNY汇率
- COMEX SI0单位：美分/盎司，需转换为元/千克
- 换算：美分/盎司 × 汇率 × 0.321507 = 元/千克

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak
import requests

SYMBOL = "AG"

def fetch_usd_cny():
    try:
        r = requests.get(
            'https://hq.sinajs.cn/list=USDCNY,USDCNH',
            headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        r.encoding = 'utf-8'
        for line in r.text.strip().split('\n'):
            if 'USDCNY' in line and 'pv_none' not in line:
                parts = line.split('"')[1].split(',')
                if len(parts) > 1:
                    return float(parts[1])
    except Exception as e:
        print(f"  汇率获取失败: {e}")
    return None

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    obs_str = obs_date.strftime("%Y-%m-%d")
    print(f"=== AG_SPD_SHFE_COMEX === obs={obs_date}")

    def get_close_col(df):
        for c in df.columns:
            if '收盘' in str(c) or '最新' in str(c):
                return c
        return df.columns[-1]

    ag_df = None
    si_df = None
    try:
        ag_df = ak.futures_main_sina("AG0")
        si_df = ak.futures_main_sina("SI0")
        rate = fetch_usd_cny()

        if ag_df is not None and len(ag_df) > 0:
            ag_close = float(ag_df.iloc[-1][get_close_col(ag_df)])
            print(f"  沪银AG: {ag_close} 元/kg")
        else:
            print("  沪银AG无数据"); ag_close = None

        if si_df is not None and len(si_df) > 0:
            si_close = float(si_df.iloc[-1][get_close_col(si_df)])
            # COMEX SI单位：美分/盎司 → 元/千克
            si_cny_kg = si_close * rate * 0.321507
            print(f"  COMEX SI: {si_close} 美分/oz = {si_cny_kg:.2f} 元/kg (汇率={rate})")
        else:
            print("  COMEX SI无数据"); si_close = None

        if ag_close and si_close and rate:
            ratio = round(ag_close / si_cny_kg, 4)
            print(f"  比价: {ag_close} / {si_cny_kg:.2f} = {ratio}")
            save_to_db("AG_SPD_SHFE_COMEX", SYMBOL, pub_date, obs_date, ratio,
                       source_confidence=1.0, source="sina_期货AG0_SI0+新浪汇率")
            print(f"[OK] AG_SPD_SHFE_COMEX={ratio} 写入成功")
            return
    except Exception as e:
        print(f"[L1] 失败: {e}")

    val = get_latest_value("AG_SPD_SHFE_COMEX", SYMBOL)
    if val is not None:
        save_to_db("AG_SPD_SHFE_COMEX", SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f"[OK] AG_SPD_SHFE_COMEX={val} L4回补成功")

if __name__ == "__main__":
    main()
