#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算期现基差.py
因子: AL_SPD_BASIS = 沪铝期现基差（元/吨）

公式: 基差 = 沪铝现货价 - 沪铝期货主力价格

当前状态: [⛔永久跳过]
- L1: AKShare futures_spot_price 对铝返回空数据
- L2: AKShare futures_zh_spot 接口故障（Sina数据格式变更）
- L3: save_l4_fallback() 无历史数据
- 不写占位符

订阅优先级: ★★★★
替代付费源: Mysteel年费 | SMM年费（沪铝现货报价）
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AL_SPD_BASIS"
SYMBOL = "AL"


def fetch_spot():
    """尝试获取沪铝现货价"""
    sym_list = ["铝", "沪铝", "AL", "alu", "Aluminum"]
    print("[L1] AKShare futures_spot_price 尝试获取沪铝现货价...")
    for sym in sym_list:
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
    """获取AL0期货价格"""
    print("[L1] AKShare futures_main_sina AL0 获取期货价...")
    try:
        df = ak.futures_main_sina(symbol="AL0")
        if df is None or len(df) == 0:
            raise ValueError("AL0无数据")
        col_map = {str(c).strip(): c for c in df.columns}
        for close_name in ["结算价", "收盘价", "最新价"]:
            if close_name in col_map:
                val = float(df.iloc[-1][col_map[close_name]])
                print(f"[L1] AL0期货={val} 元/吨")
                return val
    except Exception as e:
        print(f"[L1] AL0期货获取失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    spot_val, spot_obs = fetch_spot()
    fut_val = fetch_future()

    if spot_val is not None and fut_val is not None:
        basis = round(spot_val - fut_val, 4)
        print(f"[L1] 期现基差={spot_val} - {fut_val} = {basis} 元/吨")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, basis,
                   source_confidence=1.0, source="akshare_spot+future")
        print(f"[OK] {FACTOR_CODE}={basis} 写入成功")
        return

    # L2: 无备源（铝现货价无免费数据）
    print("[L2] 无备源（沪铝现货价依赖付费源）")

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
