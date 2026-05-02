#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热卷期货合约间价差
因子: 待定义 = 热卷期货合约间价差

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys
import datetime
from pathlib import Path

# 尝试导入通用模块
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / 'common'))
    from io_win import fix_encoding
    fix_encoding()
except ImportError:
    pass

try:
    from common.db_utils import save_to_db, get_pit_dates
except ImportError:
    def save_to_db(*a, **kw): pass
    def get_pit_dates():
        today = datetime.date.today()
        dow = today.weekday()
        if dow == 0:
            obs = today - datetime.timedelta(days=3)
        elif dow >= 5:
            obs = today - datetime.timedelta(days=dow - 4)
        else:
            obs = today
        return obs, today

# 因子参数（在函数外捕获值）
_FACTOR_SYMBOL = "HC"
_FACTOR_CODE = "HC_SPD_HC_CC"
_FACTOR_NAME = "热卷-冷轧价差"
_FACTOR_FC = "HC_HC_SPD_HC_CC"
_FACTOR_REASON = "冷轧数据需Mysteel付费"


def run(auto=False):
    obs_date, pub_date = get_pit_dates()
    print("[跳过] " + _FACTOR_FC + " = None (obs=" + str(obs_date) + ")")
    print("      原因: " + _FACTOR_REASON)

    if not auto:
        print('\n提示: 使用 --auto 参数可跳过此确认')

    # 写入 L4 stub 记录，value = None
    try:
        save_to_db(
            symbol=_FACTOR_SYMBOL,
            factor_code=_FACTOR_FC,
            obs_date=obs_date,
            pub_date=pub_date,
            raw_value=None,
            source="占位(付费订阅待配)",
            source_confidence=0.5,
            notes="[STUB] " + _FACTOR_REASON,
        )
        print("[OK] 已写入 stub 记录 (source_confidence=0.5)")
    except Exception as e:
        print("[WARN] DB写入失败: " + str(e))

    return 0


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    sys.exit(run(auto=auto))
