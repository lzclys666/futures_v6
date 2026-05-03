#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config.paths import PROJECT_ROOT
"""
风控开关功能测试（含技术反转）
"""

import sys
from pathlib import Path

# Add project path
project_dir = PROJECT_ROOT
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from strategies.macro_demo_strategy import MacroDemoStrategy
from datetime import datetime


def create_base_bars(count=100, start_price=15000):
    """创建基础数据（价格横盘）"""
    bars = []
    base_time = datetime(2025, 2, 3, 9, 0, 0)
    
    for i in range(count):
        price = start_price + (i % 10) * 2  # 小幅波动
        bar = BarData(
            symbol="RU2505",
            exchange=Exchange.SHFE,
            datetime=base_time.replace(minute=i % 60, hour=9 + i // 60),
            open_price=price,
            high_price=price + 5,
            low_price=price - 5,
            close_price=price,
            volume=100,
            open_interest=1000,
            gateway_name="BACKTESTING"
        )
        bars.append(bar)
    
    return bars


def test_all_risk_disabled():
    """测试关闭所有风控（包括技术反转）"""
    print("=== 测试关闭所有风控 ===")
    
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol='RU2505.SHFE',
        interval=Interval.MINUTE,
        start=datetime(2025, 1, 1),
        end=datetime(2025, 4, 24),
        rate=0.0001,
        slippage=2,
        size=10,
        pricetick=1,
        capital=1_000_000,
        mode=BacktestingMode.BAR
    )
    
    engine.add_strategy(
        MacroDemoStrategy,
        {
            'fast_window': 5,
            'slow_window': 10,
            'use_macro': False,
            'enable_stop_loss': False,    # 关闭止损
            'enable_take_profit': False,  # 关闭止盈
            'enable_trailing_stop': False,  # 关闭移动止损
            'enable_tech_exit': False,    # 关闭技术反转
            'stop_loss': 30,
            'take_profit': 1000,
            'trailing_stop': 1000
        }
    )
    
    # 创建测试数据：全部横盘，无趋势变化
    bars = create_base_bars(110)
    
    engine.history_data = bars
    engine.run_backtesting()
    
    print(f"交易次数: {len(engine.trades)}")
    for trade in engine.trades.values():
        print(f"  {trade.datetime} | {trade.direction.value} | 价格:{trade.price}")
    
    # 关闭所有风控后，应该只有开仓，不会平仓
    if len(engine.trades) <= 1:
        print("[PASS] 所有风控关闭测试通过 - 未触发任何平仓")
    else:
        print("[WARN] 交易次数异常，可能有未关闭的风控")


def test_only_tech_exit():
    """测试只开启技术反转"""
    print("\n=== 测试只开启技术反转 ===")
    
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol='RU2505.SHFE',
        interval=Interval.MINUTE,
        start=datetime(2025, 1, 1),
        end=datetime(2025, 4, 24),
        rate=0.0001,
        slippage=2,
        size=10,
        pricetick=1,
        capital=1_000_000,
        mode=BacktestingMode.BAR
    )
    
    engine.add_strategy(
        MacroDemoStrategy,
        {
            'fast_window': 5,
            'slow_window': 10,
            'use_macro': False,
            'enable_stop_loss': False,
            'enable_take_profit': False,
            'enable_trailing_stop': False,
            'enable_tech_exit': True,     # 只开启技术反转
            'stop_loss': 30,
            'take_profit': 1000,
            'trailing_stop': 1000
        }
    )
    
    # 创建测试数据：先横盘，然后形成死叉
    bars = create_base_bars(100)
    
    # 添加下跌数据形成死叉
    base_time = datetime(2025, 2, 3, 11, 0, 0)
    for i in range(10):
        price = 15000 - (i + 1) * 10  # 快速下跌形成死叉
        bar = BarData(
            symbol="RU2505",
            exchange=Exchange.SHFE,
            datetime=base_time.replace(minute=i),
            open_price=price,
            high_price=price + 5,
            low_price=price - 5,
            close_price=price,
            volume=100,
            open_interest=1000,
            gateway_name="BACKTESTING"
        )
        bars.append(bar)
    
    engine.history_data = bars
    engine.run_backtesting()
    
    print(f"交易次数: {len(engine.trades)}")
    for trade in engine.trades.values():
        print(f"  {trade.datetime} | {trade.direction.value} | 价格:{trade.price}")
    
    # 只开启技术反转，应该有开仓和平仓
    if len(engine.trades) >= 2:
        print("[PASS] 技术反转测试通过 - 技术反转触发平仓")
    else:
        print("[WARN] 交易次数不足")


if __name__ == "__main__":
    test_all_risk_disabled()
    test_only_tech_exit()
    print("\n测试完成！")
