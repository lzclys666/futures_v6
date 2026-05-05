#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HC_热卷期现基差
因子: HC_SPD_BASIS = 热卷期现基差

公式: 数据采集（无独立计算公式）

当前状态: [永久跳过]
- 无免费热卷现货价格数据
- 不写占位符（SOP §7）

订阅优先级: 无
替代付费源: 无
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

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

try:
    from common.db_utils import get_pit_dates
except ImportError:
    def get_pit_dates():
        today = datetime.date.today()
        dow = today.weekday()
        if dow == 0:
            obs = today - datetime.timedelta(days=3)
        elif dow >= 5:
            obs = today - datetime.timedelta(days=dow - 4)
        else:
            obs = today
        return today, obs

# 因子参数
_FACTOR_SYMBOL = "HC"
_FACTOR_CODE = "HC_SPD_BASIS"
_FACTOR_NAME = "热卷期现基差"
_FACTOR_REASON = "无免费热卷现货价格数据"


def run(auto=False):
    pub_date, obs_date = get_pit_dates()
    print(f"[跳过] {_FACTOR_CODE} = None (obs={obs_date})")
    print(f"      原因: {_FACTOR_REASON}")

    if not auto:
        print('\n提示: 使用 --auto 参数可跳过此确认')

    return 0


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    sys.exit(run(auto=auto))
