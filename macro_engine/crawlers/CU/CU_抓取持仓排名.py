#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取持仓排名
因子: CU_POS_NET = 抓取持仓排名

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date, timedelta

FACTOR_CODE = "CU_POS_NET"
SYMBOL = "CU"
EXPECTED_MIN = -200000
EXPECTED_MAX = 200000

def get_last_trading_day():
    today = date.today()
    for days_back in range(30):
        d = today - timedelta(days=days_back)
        if d.weekday() < 5:
            return d
    return today

def fetch():
    obs_date = get_last_trading_day()
    date_str = obs_date.strftime('%Y%m%d')
    r = ak.get_shfe_rank_table(date=date_str, vars_list=['CU'])
    if not r:
        raise ValueError("SHFE CU持仓排名返回空 date=%s" % date_str)
    # 取主力合约(持仓量最大的合约)
    contracts = {k: v for k, v in r.items() if str(k).startswith('cu')}
    if not contracts:
        raise ValueError("无CU合约数据 keys=%s" % list(r.keys()))
    # 取总持仓量最大的合约作为主力
    main_contract = max(contracts.keys(), key=lambda k: float(contracts[k]['long_open_interest'].sum()) + float(contracts[k]['short_open_interest'].sum()))
    df = contracts[main_contract]
    long_sum = float(df['long_open_interest'].sum())
    short_sum = float(df['short_open_interest'].sum())
    raw_value = long_sum - short_sum
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1 FAIL] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4 Fallback] %s=%.2f" % (FACTOR_CODE, latest))
            _pub = date.today()
            _obs = get_last_trading_day()
            save_to_db(FACTOR_CODE, SYMBOL, _pub, _obs, latest,
                       source_confidence=0.5, source="db_回补")
            return
        # Null 占位写入
        _pub = date.today()
        _obs = get_last_trading_day()
        save_to_db(FACTOR_CODE, SYMBOL, _pub, _obs, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] 因子 {FACTOR_CODE} NULL 占位写入")
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print("[WARN] %s=%.1f out of [%d,%d]" % (FACTOR_CODE, raw_value, EXPECTED_MIN, EXPECTED_MAX))
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print("[OK] %s=%.1f obs=%s" % (FACTOR_CODE, raw_value, obs_date))

if __name__ == "__main__":
    main()
