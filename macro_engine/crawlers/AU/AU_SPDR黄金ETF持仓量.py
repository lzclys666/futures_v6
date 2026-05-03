#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_SPDR黄金ETF持仓量.py
因子: AU_SPD_GLD = SPDR黄金ETF持仓量（吨）

公式: 数据采集（无独立计算公式）

当前状态: [OK] 正常
- 数据源: L1a: 我的钢铁网 | L1b: 东方财富API | L1c: 新浪贵金属 | L4: DB回补
- 采集逻辑: 见脚本内多源漏斗
- bounds: 因因子而异

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
from common.web_utils import fetch_url, fetch_json

FACTOR_CODE = "AU_SPD_GLD"
SYMBOL = "AU"


def fetch_spdr():
    """尝试从多个源获取SPDR黄金持仓（吨）"""

    # L1a: 我的钢铁网 SPDR黄金持仓
    try:
        html, err = fetch_url(
            'https://news.mysteel.com/a/26041709/',
            timeout=10
        )
        if err:
            raise Exception(err)
        text = html
        # Pattern: SPDR Gold Trust持仓量为XXXX.XX吨
        m = re.search(r'SPD[Rr].*?持仓量[为]?(\d+\.?\d*)\s*吨', text)
        if not m:
            m = re.search(r'持仓[为]?(\d+\.?\d{2})\s*吨', text[:3000])
        if m:
            val = float(m.group(1))
            if 500 <= val <= 2000:
                print(f"[L1a] SPDR GLD={val}吨 (Mysteel)")
                return val, 1.0, "mysteel_spdr_gld"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 东方财富 SPDR持仓数据API
    try:
        data, err = fetch_json(
            'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_GOLD_ETF_HOLD&columns=ALL&pageNumber=1&pageSize=5',
            headers={'Referer': 'https://data.eastmoney.com/'},
            timeout=10
        )
        if err:
            raise Exception(err)
        for item in data.get('result', {}).get('data', []):
            if 'SPDR' in str(item) or 'GLD' in str(item):
                hold = item.get('F8') or item.get('hold')  # 持仓量
                if hold and 500 <= float(hold) <= 2000:
                    val = float(hold)
                    print(f"[L1b] SPDR GLD={val}吨 (Eastmoney API)")
                    return val, 1.0, "eastmoney_gold_etf"
    except Exception as e:
        print(f"[L1b] {e}")

    # L1c: 新浪贵金属
    try:
        html, err = fetch_url(
            'https://hq.sinajs.cn/list=hf_GLD',
            headers={'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        if err:
            raise Exception(err)
        m = re.search(r'"([^"]+)"', html)
        if m:
            parts = m.group(1).split(',')
            for p in parts:
                try:
                    val = float(p)
                    if 500 <= val <= 2000:
                        print(f"[L1c] SPDR GLD={val} (Sina GLD)")
                        return val, 1.0, "sina_hq_hf_GLD"
                except (ValueError, IndexError):
                    pass
    except Exception as e:
        print(f"[L1c] {e}")

    # L4: 历史回补
    latest = get_latest_value(FACTOR_CODE, SYMBOL)
    if latest is not None:
        print(f"[L4] SPDR GLD={latest}吨 (L4 fallback from DB)")
        return latest, 0.5, "L4_historical_fallback"
    else:
        print("[WARN] AU_SPD_GLD无任何数据源且DB无历史值，请手动录入")
        return None, None, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    val, conf, src = fetch_spdr()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=conf, source=src)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        print(f"[WARN] {FACTOR_CODE} 无数据")


if __name__ == "__main__":
    main()
