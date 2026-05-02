#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乙二醇工厂库存
因子: EG_STK_WARRANT = 乙二醇工厂库存

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os, datetime

if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False

FACTOR_CODE = "EG_STK_WARRANT"
SYMBOL = "EG"

def fetch_eg_inventory():
    """L1: AKShare futures_inventory_em 乙二醇"""
    try:
        df = ak.futures_inventory_em(symbol="乙二醇")
        if df is None or df.empty:
            return None
        df = df.dropna(subset=['库存'])
        if df.empty:
            return None
        latest = df.iloc[-1]
        date_str = str(latest['日期'])[:10]
        inventory = float(latest['库存'])
        change = float(latest.get('增减', 0) or 0)
        obs_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        return inventory, change, obs_date
    except Exception as e:
        sys.stderr.write(f"[L1] futures_inventory_em failed: {e}\n")
        return None

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    sys.stdout.write(f"(auto) === {FACTOR_CODE} === obs={obs_date}\n")
    sys.stdout.flush()

    if not HAS_AK:
        sys.stdout.write("[ERR] AKShare not installed\n")
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_history_fallback")
            sys.stdout.write(f"[L4] {FACTOR_CODE}={v} L4 done\n")
        return 0

    result = fetch_eg_inventory()
    if result:
        val, change, fetched_obs = result
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, fetched_obs, val,
                   source_confidence=1.0, source="AKShare futures_inventory_em")
        sys.stdout.write(f"[L1] {FACTOR_CODE}={val} change={change} ({fetched_obs}) done\n")
        return 0
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_history_fallback")
            sys.stdout.write(f"[L4] {FACTOR_CODE}={v} L4 done\n")
            return 0
        else:
            sys.stdout.write("[WARN] All sources failed\n")
            return 0

if __name__ == "__main__":
    sys.exit(main())
