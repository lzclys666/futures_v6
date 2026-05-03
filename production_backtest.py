#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config.paths import PROJECT_ROOT
"""
Production Backtest System - Correct Statistics Calculation
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
import math
import random

# Add project path
project_dir = PROJECT_ROOT
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from strategies.macro_demo_strategy import MacroDemoStrategy, SYMBOL_CONFIG


@dataclass
class BacktestResult:
    """Complete backtest result"""
    symbol: str
    config_name: str
    
    # Trade stats
    total_trades: int
    completed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # PnL stats
    total_profit: float
    total_loss: float
    net_profit: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_profit: float
    max_loss: float
    
    # Risk metrics
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    
    # Equity
    initial_capital: float
    final_capital: float
    return_pct: float
    
    # Trade list for detailed analysis
    trade_list: List[Dict]


class ProductionBacktester:
    """Production-grade backtester with correct statistics"""
    
    def __init__(self, capital: float = 1_000_000):
        self.capital = capital
        self.results: List[BacktestResult] = []
        
    def create_realistic_data(self, symbol: str, days: int = 30,
                             trend: str = "mixed", volatility: float = 0.015) -> List[BarData]:
        """Create realistic OHLC data with proper trend and volatility"""
        bars = []
        base_time = datetime(2025, 2, 3, 9, 0, 0)
        
        config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        pricetick = config['pricetick']
        
        # Price starts at realistic level for each symbol
        base_prices = {
            'RU': 15000, 'ZN': 22000, 'RB': 3500, 'NI': 130000,
            'CU': 70000, 'AL': 19000, 'AU': 480, 'AG': 5800,
            'I': 800, 'J': 2200, 'JM': 1500, 'M': 3200,
            'Y': 7500, 'P': 7200, 'C': 2600, 'TA': 5800,
            'MA': 2500, 'SR': 6100, 'CF': 15500, 'RM': 2600,
            'OI': 8800, 'SC': 550, 'NR': 11000, 'IF': 3800,
            'IC': 5800, 'IH': 2600, 'T': 103
        }
        price = base_prices.get(symbol, 15000)
        
        random.seed(42)  # Reproducible
        
        # Trend bias
        if trend == "up":
            trend_bias = 0.0005
        elif trend == "down":
            trend_bias = -0.0005
        else:
            trend_bias = 0.0
        
        for day in range(days):
            # Mixed trend: sinusoidal
            if trend == "mixed":
                day_trend = math.sin(day * 0.4) * 0.001
            else:
                day_trend = trend_bias
            
            for minute in range(240):
                # Random walk with drift
                change_pct = random.gauss(day_trend, volatility / math.sqrt(240))
                change = price * change_pct
                
                # Ensure minimum movement
                if abs(change) < pricetick:
                    change = pricetick if random.random() > 0.5 else -pricetick
                
                new_price = price + change
                new_price = round(new_price / pricetick) * pricetick
                new_price = max(new_price, pricetick * 100)
                
                # Generate realistic OHLC
                high = max(price, new_price) + abs(random.gauss(0, volatility * price * 0.3))
                low = min(price, new_price) - abs(random.gauss(0, volatility * price * 0.3))
                
                high = round(high / pricetick) * pricetick
                low = round(low / pricetick) * pricetick
                
                bar_time = base_time + timedelta(days=day, minutes=minute)
                bar = BarData(
                    symbol=f"{symbol}2505",
                    exchange=Exchange.SHFE,
                    datetime=bar_time,
                    open_price=price,
                    high_price=high,
                    low_price=low,
                    close_price=new_price,
                    volume=random.randint(50, 500),
                    open_interest=random.randint(1000, 5000),
                    gateway_name="BACKTESTING"
                )
                bars.append(bar)
                price = new_price
        
        return bars
    
    def run_backtest(self, symbol: str, config: Dict, 
                    data: Optional[List[BarData]] = None,
                    days: int = 10) -> BacktestResult:
        """Run single backtest with correct statistics"""
        
        engine = BacktestingEngine()
        sym_config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        exchange = sym_config.get('exchange', 'SHFE')
        vt_symbol = f"{symbol}2505.{exchange}"
        
        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=Interval.MINUTE,
            start=datetime(2025, 2, 3),
            end=datetime(2025, 2, 13),
            rate=0.0001,
            slippage=sym_config['pricetick'],
            size=sym_config['size'],
            pricetick=sym_config['pricetick'],
            capital=self.capital,
            mode=BacktestingMode.BAR
        )
        
        engine.add_strategy(MacroDemoStrategy, config)
        
        if data is None:
            data = self.create_realistic_data(symbol, days=days)
        
        engine.history_data = data
        engine.run_backtesting()
        
        # Calculate correct statistics
        return self._calculate_stats(engine, symbol, config)
    
    def _calculate_stats(self, engine: BacktestingEngine, symbol: str, 
                        config: Dict) -> BacktestResult:
        """Calculate correct backtest statistics"""
        
        sym_config = SYMBOL_CONFIG.get(symbol, {'size': 10})
        size = sym_config['size']
        
        # Pair trades
        trades = list(engine.trades.values())
        completed_trades = []
        open_positions = []
        
        for trade in trades:
            if trade.offset.value == '开':
                open_positions.append(trade)
            else:  # 平
                if open_positions:
                    open_trade = open_positions.pop(0)
                    
                    # Calculate PnL
                    if open_trade.direction.value == '多':
                        pnl = (trade.price - open_trade.price) * trade.volume * size
                    else:  # 空
                        pnl = (open_trade.price - trade.price) * trade.volume * size
                    
                    completed_trades.append({
                        'open_time': open_trade.datetime,
                        'close_time': trade.datetime,
                        'direction': open_trade.direction.value,
                        'open_price': open_trade.price,
                        'close_price': trade.price,
                        'volume': trade.volume,
                        'pnl': pnl
                    })
        
        total_completed = len(completed_trades)
        
        if total_completed == 0:
            return BacktestResult(
                symbol=symbol, config_name=config.get('name', 'default'),
                total_trades=len(trades), completed_trades=0,
                winning_trades=0, losing_trades=0, win_rate=0.0,
                total_profit=0.0, total_loss=0.0, net_profit=0.0,
                avg_profit=0.0, avg_loss=0.0, profit_factor=0.0,
                max_profit=0.0, max_loss=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, max_drawdown_pct=0.0,
                initial_capital=self.capital, final_capital=self.capital,
                return_pct=0.0, trade_list=[]
            )
        
        # Statistics
        profits = [t['pnl'] for t in completed_trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in completed_trades if t['pnl'] <= 0]
        
        total_profit = sum(profits) if profits else 0
        total_loss = abs(sum(losses)) if losses else 0
        net_profit = total_profit - total_loss
        
        winning = len(profits)
        losing = len(losses)
        win_rate = winning / total_completed
        
        avg_profit = total_profit / winning if winning > 0 else 0
        avg_loss = total_loss / losing if losing > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        max_profit = max(profits) if profits else 0
        max_loss = min(losses) if losses else 0
        
        # Returns for Sharpe
        returns = [t['pnl'] / self.capital for t in completed_trades]
        if len(returns) > 1:
            avg_ret = sum(returns) / len(returns)
            variance = sum((r - avg_ret) ** 2 for r in returns) / (len(returns) - 1)
            std = math.sqrt(variance) if variance > 0 else 0
            sharpe = (avg_ret / std * math.sqrt(252)) if std > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown
        equity = self.capital
        peak = equity
        max_dd = 0
        max_dd_pct = 0
        
        for trade in completed_trades:
            equity += trade['pnl']
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = dd / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        final_capital = self.capital + net_profit
        return_pct = (net_profit / self.capital) * 100
        
        return BacktestResult(
            symbol=symbol,
            config_name=config.get('name', 'default'),
            total_trades=len(trades),
            completed_trades=total_completed,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_profit=max_profit,
            max_loss=max_loss,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct * 100,
            initial_capital=self.capital,
            final_capital=final_capital,
            return_pct=return_pct,
            trade_list=completed_trades
        )
    
    def print_result(self, result: BacktestResult):
        """Print formatted result"""
        print("\n" + "="*70)
        print(f"Backtest: {result.symbol} | Config: {result.config_name}")
        print("="*70)
        
        print(f"\n[Trade Statistics]")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Completed: {result.completed_trades}")
        print(f"  Winning: {result.winning_trades}")
        print(f"  Losing: {result.losing_trades}")
        print(f"  Win Rate: {result.win_rate*100:.2f}%")
        
        print(f"\n[PnL Statistics]")
        print(f"  Total Profit: {result.total_profit:,.2f}")
        print(f"  Total Loss: {result.total_loss:,.2f}")
        print(f"  Net Profit: {result.net_profit:,.2f}")
        print(f"  Avg Profit: {result.avg_profit:,.2f}")
        print(f"  Avg Loss: {result.avg_loss:,.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"  Max Profit: {result.max_profit:,.2f}")
        print(f"  Max Loss: {result.max_loss:,.2f}")
        
        print(f"\n[Risk Metrics]")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:,.2f}")
        print(f"  Max DD %: {result.max_drawdown_pct:.2f}%")
        
        print(f"\n[Equity]")
        print(f"  Initial: {result.initial_capital:,.2f}")
        print(f"  Final: {result.final_capital:,.2f}")
        print(f"  Return: {result.return_pct:.2f}%")
        
        print("="*70)
    
    def generate_report(self, output_path: str = "production_report.json"):
        """Generate JSON report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "capital": self.capital,
            "total_results": len(self.results),
            "results": []
        }
        
        for r in self.results:
            report["results"].append({
                "symbol": r.symbol,
                "config": r.config_name,
                "trades": r.completed_trades,
                "win_rate": r.win_rate,
                "net_profit": r.net_profit,
                "profit_factor": r.profit_factor,
                "sharpe": r.sharpe_ratio,
                "max_dd_pct": r.max_drawdown_pct,
                "return_pct": r.return_pct
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nReport saved: {output_path}")


def run_production_test():
    """Run production backtest test"""
    print("="*70)
    print("Production Backtest System")
    print("="*70)
    
    backtester = ProductionBacktester(capital=1_000_000)
    
    # Test configurations
    configs = [
        {
            'name': 'Conservative',
            'fast_window': 10,
            'slow_window': 20,
            'use_macro': False,
            'enable_stop_loss': True,
            'enable_take_profit': True,
            'enable_trailing_stop': False,
            'enable_tech_exit': True,
            'stop_loss': 5000,
            'take_profit': 10000
        },
        {
            'name': 'Aggressive',
            'fast_window': 5,
            'slow_window': 10,
            'use_macro': False,
            'enable_stop_loss': True,
            'enable_take_profit': False,
            'enable_trailing_stop': True,
            'enable_tech_exit': True,
            'stop_loss': 3000,
            'trailing_stop': 2000
        }
    ]
    
    # Test symbols
    symbols = ['RU', 'ZN', 'RB']
    
    for symbol in symbols:
        print(f"\n{'='*70}")
        print(f"Testing Symbol: {symbol}")
        print(f"{'='*70}")
        
        # Generate data once per symbol
        data = backtester.create_realistic_data(symbol, days=10)
        
        for config in configs:
            result = backtester.run_backtest(symbol, config, data=data)
            backtester.print_result(result)
            backtester.results.append(result)
    
    # Generate report
    backtester.generate_report(str(PROJECT_ROOT / "production_report.json"))
    
    print("\n" + "="*70)
    print("Backtest Complete!")
    print("="*70)


if __name__ == "__main__":
    run_production_test()
