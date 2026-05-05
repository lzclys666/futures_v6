#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_计算焦煤月差.py
因子: JM_SPD_CONTRACT = 焦煤期货近远月价差

公式: JM_SPD_CONTRACT = 近月合约结算价 - 远月合约结算价（元/吨）

当前状态: [✅正常]
- L1: AKShare futures_zh_daily_sina 多合约枚举（1/5/9月）+ 持仓量排序选主力
- L2: 新浪实时API hq.sinajs.cn — 多合约实时价格
- L3: 无备源（近远月价差需多合约数据）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from web_utils import fetch_url
import datetime

SYMBOL = "JM"
FACTOR_CODE = "JM_SPD_CONTRACT"
BOUNDS = (-300, 300)


def get_active_contracts():
    """获取大商所焦煤活跃合约列表(1,5,9月)"""
    today = datetime.date.today()
    y, m = today.year, today.month
    months = [1, 5, 9]
    contracts = []
    for my in range(y, y + 2):
        for mm in months:
            dt = datetime.date(my, mm, 1)
            if dt > today - datetime.timedelta(days=30):
                contracts.append(f"JM{str(my)[2:]}{mm:02d}")
    return sorted(contracts)


def fetch_contract_settle(contract):
    """获取单个合约最新结算价"""
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is not None and len(df) > 0 and 'settle' in df.columns:
            settle = float(df.iloc[-1]['settle'])
            hold = float(df.iloc[-1]['hold'])
            return settle, hold
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return None, None


def fetch_spread():
    """四层漏斗获取月差"""
    contracts = get_active_contracts()
    print(f"  候选合约: {contracts}")

    # L1: AKShare 多合约结算价
    try:
        print("[L1] AKShare futures_zh_daily_sina 多合约...")
        results = []
        for c in contracts:
            settle, hold = fetch_contract_settle(c)
            if settle and hold and hold > 0:
                results.append((c, settle, hold))
                print(f"    {c}: settle={settle}, hold={hold}")

        if len(results) >= 2:
            results.sort(key=lambda x: x[2], reverse=True)
            near = results[0]
            far = results[1] if results[1][2] > 10000 else (results[-1] if len(results) > 2 else None)
            if far:
                spread = near[1] - far[1]
                print(f"[L1] 成功: {near[0]}({near[1]}) - {far[0]}({far[1]}) = {spread}")
                return spread, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪实时API
    try:
        print("[L2] 新浪实时API...")
        if len(contracts) >= 2:
            url = f"http://hq.sinajs.cn/list=nf_{contracts[0]},nf_{contracts[1]}"
            html, err = fetch_url(url, timeout=10)
            if not err and html:
                lines = html.strip().split('\n')
                prices = []
                for line in lines:
                    if '"' in line:
                        parts = line.split('"')[1].split(',')
                        if len(parts) >= 5 and parts[4]:
                            prices.append(float(parts[4]))
                if len(prices) >= 2:
                    spread = prices[0] - prices[1]
                    print(f"[L2] 成功: {spread}")
                    return spread, 'sina', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    # L3: 无备源（近远月价差需多合约数据）

    # L4: DB历史最新值回补
    # 由 main() 中的 save_l4_fallback() 处理
    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        value, source, confidence = fetch_spread()
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
