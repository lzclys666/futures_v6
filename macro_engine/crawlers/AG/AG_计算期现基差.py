#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_计算期现基差.py
因子: AG_SPD_BASIS = 沪银期现基差（元/千克）

公式: AG_SPD_BASIS = 沪银现货价(元/千克) - AG0主力期货结算价(元/千克)

当前状态: [⛔永久跳过]
- L1: 沪银现货价依赖 AG_抓取现货价.py（该脚本已⛔永久跳过）
- L1: AG0期货价格可从 AG_抓取期货日行情.py 获取
- 因现货价无免费数据，期现基差无法计算
- L2: 无其他免费沪银现货价数据源
- L3: save_l4_fallback() 也无历史数据

订阅优先级: ★★★
替代付费源: Mysteel年费 | SMM年费 | 隆众资讯年费
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_SPD_BASIS"
SYMBOL = "AG"


def fetch_spot():
    """尝试获取沪银现货价"""
    SYM_ALTERNATIVES = ["沪银", "白银", "AG", "ag", "Silver", "silver"]
    print("[L1] 尝试AKShare futures_spot_price 获取沪银现货价...")
    for sym in SYM_ALTERNATIVES:
        try:
            import pandas as pd
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            df = ak.futures_spot_price(symbol=sym, date=today)
            if df is not None and len(df) > 0:
                row = df.iloc[-1]
                val = float(row.get('均价', row.iloc[-1]))
                obs_str = str(row.get('日期', today))[:10]
                print(f"[L1] futures_spot_price(symbol='{sym}') = {val}")
                return val, obs_str
        except Exception as e:
            print(f"[L1] symbol='{sym}' 失败: {e}")
        continue
    return None, None


def fetch_future():
    """获取AG0期货价格"""
    print("[L1] AKShare futures_main_sina AG0 获取期货价...")
    try:
        df = ak.futures_main_sina(symbol="AG0")
        if df is None or len(df) == 0:
            raise ValueError("AG0无数据")
        col_map = {str(c).strip(): c for c in df.columns}
        for close_name in ["结算价", "收盘价", "最新价"]:
            if close_name in col_map:
                val = float(df.iloc[-1][col_map[close_name]])
                print(f"[L1] AG0期货={val} 元/kg")
                return val
    except Exception as e:
        print(f"[L1] AG0期货获取失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    # L1: 尝试获取现货价和期货价
    spot_val, spot_obs = fetch_spot()
    fut_val = fetch_future()

    if spot_val is not None and fut_val is not None:
        basis = round(spot_val - fut_val, 4)
        print(f"[L1] 期现基差={spot_val} - {fut_val} = {basis} 元/kg")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, basis,
                   source_confidence=1.0, source="akshare_spot+future")
        print(f"[OK] {FACTOR_CODE}={basis} 写入成功")
        return

    # L2: 无备源（沪银现货价无免费数据）
    print("[L2] 无备源（沪银现货价依赖付费源）")

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(期现基差)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} ⛔永久跳过（无免费源: Mysteel/SMM/隆众）")


if __name__ == "__main__":
    main()
