#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乙二醇期货收盘价
因子: EG_FUT_CLOSE = 乙二醇期货收盘价

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
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

FACTOR_CODE = "EG_FUT_CLOSE"
SYMBOL = "EG"

def run(auto=False):
    """可直接import调用（用于run_all.py），也支持命令行"""
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

    try:
        df = ak.futures_main_sina(symbol="EG0")
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df = df.dropna(subset=['收盘价'])
        latest = df.iloc[-1]
        date_str = str(latest['日期'])[:10]
        close = float(latest['收盘价'])
        fetched_obs = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, fetched_obs, close,
                   source_confidence=1.0, source="AKShare futures_main_sina EG0")
        sys.stdout.write(f"[L1] {FACTOR_CODE}={close} ({fetched_obs}) done\n")
        return 0
    except Exception as e:
        sys.stderr.write(f"[L1] AKShare EG0 failed: {e}\n")
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
    auto_flag = "--auto" in sys.argv
    sys.exit(run(auto=auto_flag))
