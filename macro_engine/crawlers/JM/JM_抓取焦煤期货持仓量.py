#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_抓取焦煤期货持仓量.py
因子: JM_POS_OI = 焦煤期货持仓量

公式: JM_POS_OI = 持仓量（手）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("JM0") — 主力合约持仓量
- L2: AKShare futures_zh_daily_sina("JM0") — 日行情持仓量
- L3: 新浪实时API hq.sinajs.cn/list=nf_JM0 — 实时持仓
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from web_utils import fetch_url

SYMBOL = "JM"
FACTOR_CODE = "JM_POS_OI"
BOUNDS = (0, 1000000)


def fetch_oi():
    """四层漏斗获取持仓量"""
    # L1: AKShare futures_main_sina
    try:
        print("[L1] AKShare futures_main_sina...")
        df = ak.futures_main_sina(symbol="JM0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            hold_col = None
            for c in cols:
                if 'hold' in str(c).lower() or '持仓' in str(c):
                    hold_col = c
                    break
            if hold_col is None:
                hold_col = cols[6] if len(cols) > 6 else cols[-1]
            val = df.iloc[-1][hold_col]
            if isinstance(val, str):
                val = val.replace(',', '').strip()
            val = float(val)
            if 0 <= val <= 1000000:
                print(f"[L1] 成功: {val} 手")
                return val, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: AKShare futures_zh_daily_sina
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df = ak.futures_zh_daily_sina(symbol="JM0")
        if df is not None and len(df) > 0 and 'hold' in df.columns:
            val = float(df.iloc[-1]['hold'])
            if 0 <= val <= 1000000:
                print(f"[L2] 成功: {val} 手")
                return val, 'akshare', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    # L3: 新浪实时API
    try:
        print("[L3] 新浪实时API...")
        url = "http://hq.sinajs.cn/list=nf_JM0"
        html, err = fetch_url(url, timeout=10)
        if not err and html:
            data = html.split('"')[1].split(',') if '"' in html else []
            if len(data) >= 13:
                val = float(data[11])
                if 0 <= val <= 1000000:
                    print(f"[L3] 成功: {val} 手")
                    return val, 'sina', 0.8
    except Exception as e:
        print(f"[L3] 失败: {e}")

    # L4: DB历史最新值回补
    # 由 main() 中的 save_l4_fallback() 处理
    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        value, source, confidence = fetch_oi()
        if value is None:
            print(f"[L1-L3 FAIL] {FACTOR_CODE} 所有数据源均失败")
            save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
            return
        if not (BOUNDS[0] <= value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source_confidence=confidence, source=source)
        print(f"[OK] {FACTOR_CODE}={value} obs={obs_date}")
    except Exception as e:
        print(f"[ERR] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
