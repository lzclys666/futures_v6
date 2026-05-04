#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取汇率.py
因子: AG_COST_USDCNY = 美元兑人民币汇率（USDCNY）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: 新浪财经 hq.sinajs.cn/list=USDCNY（实时汇率）
- L2: AKShare forex.forex_em 外汇实时数据（备用）
- bounds: [6.5, 7.5]（USDCNY合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url
import re

SYMBOL = "AG"
FACTOR_CODE = "AG_COST_USDCNY"
EMIN = 6.5
EMAX = 7.5


def fetch_sina():
    # L1: 新浪财经 USDCNY
    try:
        html, err = fetch_url('https://hq.sinajs.cn/list=USDCNY', timeout=10,
                             headers={'Referer': 'https://finance.sina.com.cn'})
        if err:
            raise Exception(err)
        m = re.search(r'"([^"]+)"', html)
        if m:
            parts = m.group(1).split(',')
            val = float(parts[8])
            if not (EMIN <= val <= EMAX):
                print(f"[L1] Sina USDCNY={val} 超出bounds[{EMIN},{EMAX}]")
                return None
            print(f"[L1] Sina USDCNY={val}")
            return val
    except Exception as e:
        print(f"[L1] 新浪失败: {e}")
    return None


def fetch_akshare():
    # L2: AKShare 外汇
    try:
        import akshare.forex.forex_em as fe
        df = fe.forex_spot_em()
        for _, row in df.iterrows():
            name = str(row.get('名称', ''))
            if '美元' in name or 'USD' in name.upper():
                val = float(row.get('最新价', 0))
                if not (EMIN <= val <= EMAX):
                    print(f"[L2] AKShare USDCNY={val} 超出bounds[{EMIN},{EMAX}]")
                    return None
                print(f"[L2] AKShare USDCNY={val}")
                return val
    except Exception as e:
        print(f"[L2] AKShare失败: {e}")
    return None


def fetch():
    val = fetch_sina()
    if val is None:
        val = fetch_akshare()
    return val


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="sina_hq_USDCNY")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(USDCNY汇率)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
