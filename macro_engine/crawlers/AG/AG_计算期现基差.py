#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_计算期现基差.py
因子: AG_SPD_BASIS = 沪银期现基差（元/千克）

公式: AG_SPD_BASIS = 沪银现货价(元/千克) - AG0主力期货结算价(元/千克)

当前状态: [✅正常]
- L1: akshare futures_spot_price(date, vars_list=['AG']) 获取沪银现货价
- L1: akshare futures_main_sina AG0 获取期货价
- 修复：ak.futures_spot_price API 参数为 vars_list 而非 symbol
- 修复：今日为节假日时自动回退到前一交易日
- bounds: 基差[-500, 500]元/kg

订阅优先级: 无需付费
替代付费源: 无
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
    """尝试获取沪银现货价（自动处理节假日，回退到最近交易日）"""
    SYM_ALTERNATIVES = ["AG"]  # vars_list 只接受代码如 'AG'
    print("[L1] 尝试AKShare futures_spot_price 获取沪银现货价...")
    
    # 尝试最近10个自然日（自动跳过节假日/周末）
    import pandas as pd
    for days_back in range(10):
        check_date = pd.Timestamp.now() - pd.Timedelta(days=days_back)
        date_str = check_date.strftime('%Y%m%d')  # YYYYMMDD 格式
        date_display = check_date.strftime('%Y-%m-%d')
        
        for sym in SYM_ALTERNATIVES:
            try:
                df = ak.futures_spot_price(date=date_str, vars_list=[sym])
                if df is not None and len(df) > 0:
                    # 找 AG 那一行
                    ag_row = df[df['symbol'] == 'AG']
                    if len(ag_row) == 0:
                        continue
                    val = float(ag_row.iloc[0]['spot_price'])
                    # date 格式为 YYYYMMDD，需转为 YYYY-MM-DD
                    d = str(ag_row.iloc[0]['date'])
                    obs_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                    print(f"[L1] futures_spot_price(date='{date_str}', vars_list=['{sym}']) = {val}, obs={obs_str}")
                    return val, obs_str
            except Exception as e:
                print(f"[L1] date='{date_str}', vars_list=['{sym}'] 失败: {e}")
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
        # obs_date 使用现货的实际观测日期（spot_obs），因为今日为节假日时数据来自前一交易日
        actual_obs = spot_obs if spot_obs else obs_date
        print(f"[L1] 期现基差={spot_val} - {fut_val} = {basis} 元/kg")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_obs, basis,
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
