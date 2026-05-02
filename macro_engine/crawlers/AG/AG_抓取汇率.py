#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取汇率.py
因子: AG_COST_USDCNY = 美元兑人民币汇率（USDCNY）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: 新浪财经 hq.sinajs.cn/list=USDCNY（实时汇率）
- L2: AKShare forex.forex_em 外汇实时数据（备用）
- bounds: [6.5, 7.5]（USDCNY合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import requests
import re
import akshare.forex.forex_em as fe

SYMBOL = "AG"
EMIN = 6.5
EMAX = 7.5

def fetch_sina():
    try:
        r = requests.get('https://hq.sinajs.cn/list=USDCNY', timeout=10,
                        headers={'Referer': 'https://finance.sina.com.cn'})
        r.encoding = 'gbk'
        m = re.search(r'"([^"]+)"', r.text)
        if m:
            parts = m.group(1).split(',')
            val = float(parts[8])
            print(f"[L1] Sina USDCNY={val}")
            return val
    except Exception as e:
        print(f"[L1] Sina失败: {e}")
    return None

def fetch_akshare():
    try:
        df = fe.forex_spot_em()
        for _, row in df.iterrows():
            name = str(row.get('名称', ''))
            if '美元' in name or 'USD' in name.upper():
                val = float(row.get('最新价', 0))
                print(f"[L2] AKShare USDCNY={val}")
                return val
    except Exception as e:
        print(f"[L2] AKShare失败: {e}")
    return None

def fetch():
    val = fetch_sina()
    if val is None:
        val = fetch_akshare()
    if val is not None and not (EMIN <= val <= EMAX):
        print(f"[校验失败] USDCNY={val} 超出范围[{EMIN},{EMAX}]")
        return None
    return val

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== AG_COST_USDCNY === obs={obs_date}")
    val = fetch()
    if val is not None:
        save_to_db("AG_COST_USDCNY", SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="sina_hq_USDCNY")
        print(f"[OK] AG_COST_USDCNY={val} 写入成功")
    else:
        v = get_latest_value("AG_COST_USDCNY", SYMBOL)
        if v is not None:
            save_to_db("AG_COST_USDCNY", SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_回补")
            print(f"[OK] AG_COST_USDCNY={v} L4回补")

if __name__ == "__main__":
    main()
