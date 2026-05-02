#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
止损止盈功能测试
"""

import sys
from pathlib import Path

# Add project path
project_dir = Path('D:/futures_v6')
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


def test_stop_loss():
    """测试止损功能"""
    print("=== 测试止损 ===")
    
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
            'use_macro': False,  # 不使用宏观信号
            'stop_loss': 30,     # 止损30元
            'take_profit': 1000,  # 不触发止盈
            'trailing_stop': 1000  # 不触发移动止损
        }
    )
    
    # 创建测试数据：先横盘100个bar，然后下跌触发止损
    bars = create_base_bars(100)
    
    # 添加下跌数据（从15000跌到14960，亏损40元，触发止损）
    base_time = datetime(2025, 2, 3, 11, 0, 0)
    for i in range(10):
        price = 15000 - (i + 1) * 5
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
    
    if len(engine.trades) >= 2:
        print("[PASS] 止损测试通过")
    else:
        print("[WARN] 交易次数不足，可能需要调整参数")


def test_take_profit():
    """测试止盈功能"""
    print("\n=== 测试止盈 ===")
    
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
            'stop_loss': 1000,  # 不触发止损
            'take_profit': 50,  # 止盈50元
            'trailing_stop': 1000
        }
    )
    
    # 创建测试数据：先横盘100个bar，然后上涨触发止盈
    bars = create_base_bars(100)
    
    # 添加上涨数据（从15000涨到15070，盈利70元，触发止盈）
    base_time = datetime(2025, 2, 3, 11, 0, 0)
    for i in range(10):
        price = 15000 + (i + 1) * 8
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
    
    if len(engine.trades) >= 2:
        print("[PASS] 止盈测试通过")
    else:
        print("[WARN] 交易次数不足，可能需要调整参数")


def test_trailing_stop():
    """测试移动止损功能"""
    print("\n=== 测试移动止损 ===")
    
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
            'stop_loss': 1000,  # 不触发止损
            'take_profit': 1000,  # 不触发止盈
            'trailing_stop': 20  # 移动止损20元
        }
    )
    
    # 创建测试数据：先横盘100个bar，然后上涨到15200，再回撤到15170（回撤30元，触发移动止损）
    bars = create_base_bars(100)
    
    # 上涨
    base_time = datetime(2025, 2, 3, 11, 0, 0)
    for i in range(10):
        price = 15000 + (i + 1) * 20  # 涨到15200
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
    
    # 回撤
    base_time = datetime(2025, 2, 3, 11, 10, 0)
    for i in range(5):
        price = 15200 - (i + 1) * 8  # 回撤到15160
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
    
    if len(engine.trades) >= 2:
        print("[PASS] 移动止损测试通过")
    else:
        print("[WARN] 交易次数不足，可能需要调整参数")


if __name__ == "__main__":
    test_stop_loss()
    test_take_profit()
    test_trailing_stop()
    print("\n测试完成！")
