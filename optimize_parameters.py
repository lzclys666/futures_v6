#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数优化脚本 - 测试不同的 fast_window/slow_window 组合
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
import pandas as pd
from datetime import datetime


def load_data(data_path: Path) -> list:
    """加载历史数据"""
    df = pd.read_csv(data_path)
    bars = []
    for _, row in df.iterrows():
        bar = BarData(
            symbol="RU2505",
            exchange=Exchange.SHFE,
            datetime=pd.to_datetime(row['datetime']),
            open_price=row['open'],
            high_price=row['high'],
            low_price=row['low'],
            close_price=row['close'],
            volume=row['volume'],
            open_interest=row['open_interest'],
            gateway_name="BACKTESTING"
        )
        bars.append(bar)
    return bars


def run_backtest(fast_window: int, slow_window: int, bars: list) -> dict:
    """运行回测"""
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
            'fast_window': fast_window,
            'slow_window': slow_window,
            'use_macro': True,
            'csv_path_str': str(project_dir / 'macro_engine/output/{symbol}_macro_daily_{date}.csv')
        }
    )
    
    engine.history_data = bars
    engine.run_backtesting()
    
    # Calculate metrics
    total_trades = len(engine.trades)
    
    # Calculate P&L
    pnl = 0
    for trade in engine.trades.values():
        if trade.direction.value == "多":  # LONG
            pnl += (trade.price - trade.price) * trade.volume * 10  # Simplified
        else:
            pnl -= (trade.price - trade.price) * trade.volume * 10
    
    return {
        'fast_window': fast_window,
        'slow_window': slow_window,
        'total_trades': total_trades,
        'pnl': pnl
    }


def main():
    """主函数"""
    print("=== 参数优化开始 ===")
    
    # Load data once
    data_path = project_dir / 'data' / 'historical' / 'RU2505_1min.csv'
    bars = load_data(data_path)
    print(f"Loaded {len(bars)} bars")
    
    # Parameter grid
    fast_windows = [5, 10, 15, 20]
    slow_windows = [20, 30, 40, 60]
    
    results = []
    
    for fast in fast_windows:
        for slow in slow_windows:
            if fast >= slow:
                continue
            
            print(f"\nTesting fast={fast}, slow={slow}...")
            result = run_backtest(fast, slow, bars)
            results.append(result)
            print(f"  Trades: {result['total_trades']}")
    
    # Print results
    print("\n=== 参数优化结果 ===")
    print(f"{'Fast':<6} {'Slow':<6} {'Trades':<8}")
    print("-" * 25)
    for r in results:
        print(f"{r['fast_window']:<6} {r['slow_window']:<6} {r['total_trades']:<8}")
    
    # Find best parameters
    best = max(results, key=lambda x: x['total_trades'])
    print(f"\n最佳参数: fast={best['fast_window']}, slow={best['slow_window']}")
    print(f"交易次数: {best['total_trades']}")


if __name__ == "__main__":
    main()
