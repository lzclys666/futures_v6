#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化回测验证 - 使用真实价格序列测试策略逻辑
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project path
project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from strategies.macro_demo_strategy import MacroDemoStrategy


def create_simple_trend_data(symbol: str, days: int = 5) -> list:
    """创建简单的趋势数据：明确的上涨后下跌，形成金叉死叉"""
    bars = []
    base_time = datetime(2025, 2, 3, 9, 0, 0)
    
    # 前3天：持续上涨形成金叉
    price = 14000
    for day in range(3):
        for minute in range(240):
            # 每天上涨100点
            price += 100 / 240
            
            bar = BarData(
                symbol=f"{symbol}2505",
                exchange=Exchange.SHFE,
                datetime=base_time + timedelta(days=day, minutes=minute),
                open_price=price - 2,
                high_price=price + 5,
                low_price=price - 5,
                close_price=price,
                volume=100,
                open_interest=1000,
                gateway_name="BACKTESTING"
            )
            bars.append(bar)
    
    # 后2天：持续下跌形成死叉
    for day in range(3, 5):
        for minute in range(240):
            # 每天下跌150点（跌幅更大）
            price -= 150 / 240
            
            bar = BarData(
                symbol=f"{symbol}2505",
                exchange=Exchange.SHFE,
                datetime=base_time + timedelta(days=day, minutes=minute),
                open_price=price + 2,
                high_price=price + 5,
                low_price=price - 5,
                close_price=price,
                volume=100,
                open_interest=1000,
                gateway_name="BACKTESTING"
            )
            bars.append(bar)
    
    return bars


def test_basic_logic():
    """测试基本交易逻辑"""
    print("="*60)
    print("基本交易逻辑测试")
    print("="*60)
    
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol='RU2505.SHFE',
        interval=Interval.MINUTE,
        start=datetime(2025, 2, 3),
        end=datetime(2025, 2, 10),
        rate=0.0001,
        slippage=2,
        size=10,
        pricetick=1,
        capital=1_000_000,
        mode=BacktestingMode.BAR
    )
    
    # 纯技术模式，关闭所有风控，只测试开仓
    config = {
        'fast_window': 5,
        'slow_window': 10,
        'use_macro': False,
        'enable_stop_loss': False,
        'enable_take_profit': False,
        'enable_trailing_stop': False,
        'enable_tech_exit': False,  # 关闭技术平仓
    }
    
    engine.add_strategy(MacroDemoStrategy, config)
    
    # 创建测试数据
    bars = create_simple_trend_data('RU', days=5)
    print(f"生成K线数量: {len(bars)}")
    print(f"价格范围: {bars[0].close_price} -> {bars[-1].close_price}")
    
    engine.history_data = bars
    engine.run_backtesting()
    
    print(f"\n交易记录:")
    for trade in engine.trades.values():
        print(f"  {trade.datetime} | {trade.direction.value} | 价格:{trade.price} | 盈亏:{trade.price * 10:.2f}")
    
    print(f"\n总交易次数: {len(engine.trades)}")
    
    # 统计盈亏
    long_trades = [t for t in engine.trades.values() if t.direction.value == '多']
    short_trades = [t for t in engine.trades.values() if t.direction.value == '空']
    
    print(f"多单: {len(long_trades)}")
    print(f"空单: {len(short_trades)}")


def test_with_stop_loss():
    """测试止损功能"""
    print("\n" + "="*60)
    print("止损功能测试")
    print("="*60)
    
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol='RU2505.SHFE',
        interval=Interval.MINUTE,
        start=datetime(2025, 2, 3),
        end=datetime(2025, 2, 10),
        rate=0.0001,
        slippage=2,
        size=10,
        pricetick=1,
        capital=1_000_000,
        mode=BacktestingMode.BAR
    )
    
    # 开启止损
    config = {
        'fast_window': 5,
        'slow_window': 10,
        'use_macro': False,
        'enable_stop_loss': True,
        'stop_loss': 50,  # 50元止损
        'enable_take_profit': False,
        'enable_trailing_stop': False,
        'enable_tech_exit': False,
    }
    
    engine.add_strategy(MacroDemoStrategy, config)
    
    bars = create_simple_trend_data('RU', days=5)
    engine.history_data = bars
    engine.run_backtesting()
    
    print(f"总交易次数: {len(engine.trades)}")
    
    # 检查是否有止损平仓
    for trade in engine.trades.values():
        print(f"  {trade.datetime} | {trade.direction.value} | 价格:{trade.price}")


if __name__ == "__main__":
    test_basic_logic()
    test_with_stop_loss()
    print("\n测试完成！")
