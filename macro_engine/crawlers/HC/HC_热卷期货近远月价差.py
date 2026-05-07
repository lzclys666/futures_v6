#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HC_热卷期货近远月价差.py
因子: HC_SPD_NEAR_FAR = 热卷期货近远月价差（元/吨）

公式: HC_SPD_NEAR_FAR = 近月合约收盘价 - 远月合约收盘价

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='HC{YYMM}') — 逐合约获取收盘价
  自动枚举当前年份所有合约月份，取最近两个活跃合约计算价差
- L3: save_l4_fallback() DB历史最新值回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import date, timedelta

FCODE = "HC_SPD_NEAR_FAR"
SYM = "HC"
BOUNDS = (-500, 500)  # 价差合理范围（元/吨）
BACKOFF_DAYS = 15


def get_contract_close(contract_code, obs_date):
    """获取指定合约在obs_date或之前的最新收盘价"""
    try:
        df = ak.futures_main_sina(symbol=contract_code)
        if df is None or len(df) == 0:
            return None, None
        df['日期'] = pd.to_datetime(df['日期'])
        obs_dt = pd.Timestamp(obs_date)
        df_valid = df[df['日期'] <= obs_dt]
        if len(df_valid) == 0:
            return None, None
        row = df_valid.iloc[-1]
        return float(row['收盘价']), row['日期'].date()
    except Exception as e:
        print(f"  [ERR] futures_main_sina({contract_code}): {type(e).__name__}: {str(e)[:80]}")
        return None, None


def fetch(obs_date):
    """获取近远月价差：枚举当前年份合约，取最近两个活跃合约"""
    yy = obs_date.year % 100  # e.g. 26 for 2026

    # 收集所有活跃合约及其收盘价
    active_contracts = []
    for y in [yy, yy + 1]:
        for m in range(1, 13):
            code = f"HC{y:02d}{m:02d}"
            close, cdate = get_contract_close(code, obs_date)
            if close is not None and cdate is not None:
                # 只取obs_date附近10天内有数据的合约（活跃合约，考虑长假）
                if (obs_date - cdate).days <= 10:
                    contract_month = date(2000 + y, m, 1)
                    active_contracts.append({
                        'code': code,
                        'close': close,
                        'date': cdate,
                        'month': contract_month
                    })
                    print(f"  [INFO] {code}: close={close}, date={cdate}")

    if len(active_contracts) < 2:
        print(f"[WARN] 只找到 {len(active_contracts)} 个活跃合约，无法计算价差")
        return None, None, None

    # 按合约月份排序
    active_contracts.sort(key=lambda x: x['month'])

    near = active_contracts[0]
    far = active_contracts[1]

    spread = near['close'] - far['close']
    # 取两个合约中较早的obs_date作为实际观测日
    actual_obs = min(near['date'], far['date'])

    print(f"  [INFO] 近月={near['code']}({near['close']}), 远月={far['code']}({far['close']}), 价差={spread}")
    return spread, actual_obs, f"{near['code']}-{far['code']}"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: 合约收盘价计算价差
    raw_value, actual_obs, pair_info = fetch(obs_date)
    if raw_value is not None:
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FCODE}={raw_value} out of {BOUNDS}")
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source=f'akshare_sina_contracts({pair_info})')
        print(f"[OK] {FCODE}={raw_value} obs={actual_obs} pair={pair_info}")
        return

    print("[L1 FAIL] 合约价差计算失败, trying L3...")

    # L3: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
