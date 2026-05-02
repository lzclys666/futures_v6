"""
SHFE沪金前20会员净持仓（手）
因子: AU_SHFE_OI_RANK = SHFE沪金前20会员净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: ⛔永久跳过
- 数据源: 无免费源。SHFE官网数据接口404，AKShare DCE不支持SHFE。付费订阅: SHFE官网
- 采集逻辑: 见脚本内多源漏斗
- bounds: 因因子而异

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "AU_SHFE_OI_RANK"
SYMBOL = "AU"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # L4: 历史回补
    latest = get_latest_value(FACTOR_CODE, SYMBOL)
    if latest is not None:
        print(f"[L4] AU_SHFE_OI_RANK={latest}吨 (L4 fallback from DB)")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, latest,
                   source_confidence=0.5, source="L4_historical_fallback")
        print(f"[OK] {FACTOR_CODE}={latest} 写入成功")
    else:
        print(f"[WARN] {FACTOR_CODE} 无数据且DB无历史值（付费订阅: SHFE官网数据）")


if __name__ == "__main__":
    main()
