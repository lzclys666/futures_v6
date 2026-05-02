#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测结果分析器 - 正确计算统计指标
"""

import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict
import json
import math

# Add project path
project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))


@dataclass
class TradeRecord:
    """交易记录"""
    datetime: datetime
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    offset: str     # 'OPEN' or 'CLOSE'
    price: float
    volume: int
    size: int       # 合约乘数
    

@dataclass  
class BacktestStats:
    """回测统计结果"""
    symbol: str
    total_trades: int          # 总交易次数（开仓+平仓）
    completed_trades: int      # 完整交易次数（一对开平）
    winning_trades: int        # 盈利次数
    losing_trades: int         # 亏损次数
    win_rate: float            # 胜率
    
    total_profit: float        # 总盈利
    total_loss: float          # 总亏损
    gross_profit: float        # 毛利润
    net_profit: float          # 净利润
    avg_profit: float          # 平均盈利
    avg_loss: float            # 平均亏损
    profit_factor: float       # 盈亏比
    
    max_profit: float          # 最大单笔盈利
    max_loss: float            # 最大单笔亏损
    
    returns: List[float]       # 每笔收益率列表
    sharpe_ratio: float        # 夏普比率
    max_drawdown: float        # 最大回撤金额
    max_drawdown_pct: float    # 最大回撤百分比
    
    daily_returns: List[float] # 日收益率


class TradeAnalyzer:
    """交易分析器"""
    
    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.trades: List[TradeRecord] = []
        
    def add_trade(self, trade: TradeRecord):
        """添加交易记录"""
        self.trades.append(trade)
        
    def analyze(self, symbol: str, size: int = 10) -> BacktestStats:
        """分析交易记录，计算统计指标"""
        
        # 配对开平仓，计算每笔完整交易的盈亏
        completed_trades = []
        open_positions = []
        
        for trade in self.trades:
            if trade.offset == 'OPEN':
                open_positions.append(trade)
            else:  # CLOSE
                if open_positions:
                    open_trade = open_positions.pop(0)
                    
                    # 计算盈亏
                    if open_trade.direction == 'LONG':
                        pnl = (trade.price - open_trade.price) * trade.volume * size
                    else:  # SHORT
                        pnl = (open_trade.price - trade.price) * trade.volume * size
                    
                    completed_trades.append({
                        'open_time': open_trade.datetime,
                        'close_time': trade.datetime,
                        'direction': open_trade.direction,
                        'open_price': open_trade.price,
                        'close_price': trade.price,
                        'volume': trade.volume,
                        'pnl': pnl
                    })
        
        # 统计计算
        total_completed = len(completed_trades)
        if total_completed == 0:
            return BacktestStats(
                symbol=symbol, total_trades=len(self.trades),
                completed_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_profit=0.0, total_loss=0.0,
                gross_profit=0.0, net_profit=0.0, avg_profit=0.0,
                avg_loss=0.0, profit_factor=0.0, max_profit=0.0,
                max_loss=0.0, returns=[], sharpe_ratio=0.0,
                max_drawdown=0.0, max_drawdown_pct=0.0, daily_returns=[]
            )
        
        # 盈亏统计
        profits = [t['pnl'] for t in completed_trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in completed_trades if t['pnl'] <= 0]
        
        total_profit = sum(profits) if profits else 0
        total_loss = abs(sum(losses)) if losses else 0
        net_profit = total_profit - total_loss
        
        winning_trades = len(profits)
        losing_trades = len(losses)
        win_rate = winning_trades / total_completed
        
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        max_profit = max(profits) if profits else 0
        max_loss = min(losses) if losses else 0
        
        # 计算收益率序列
        returns = [t['pnl'] / self.initial_capital for t in completed_trades]
        
        # 夏普比率（简化版，假设无风险利率为0）
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std = math.sqrt(variance) if variance > 0 else 0
            sharpe_ratio = (avg_return / std * math.sqrt(252)) if std > 0 else 0  # 年化
        else:
            sharpe_ratio = 0
        
        # 最大回撤计算
        equity = self.initial_capital
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
        
        return BacktestStats(
            symbol=symbol,
            total_trades=len(self.trades),
            completed_trades=total_completed,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            gross_profit=total_profit - total_loss,
            net_profit=net_profit,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_profit=max_profit,
            max_loss=max_loss,
            returns=returns,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct * 100,
            daily_returns=[]
        )
    
    def print_report(self, stats: BacktestStats):
        """打印分析报告"""
        print("\n" + "="*70)
        print(f"Backtest Report: {stats.symbol}")
        print("="*70)
        
        print(f"\n[Trade Statistics]")
        print(f"  Total Trades: {stats.total_trades}")
        print(f"  Completed: {stats.completed_trades}")
        print(f"  Winning: {stats.winning_trades}")
        print(f"  Losing: {stats.losing_trades}")
        print(f"  Win Rate: {stats.win_rate*100:.2f}%")
        
        print(f"\n[PnL Statistics]")
        print(f"  Total Profit: {stats.total_profit:,.2f}")
        print(f"  Total Loss: {stats.total_loss:,.2f}")
        print(f"  Net Profit: {stats.net_profit:,.2f}")
        print(f"  Avg Profit: {stats.avg_profit:,.2f}")
        print(f"  Avg Loss: {stats.avg_loss:,.2f}")
        print(f"  Profit Factor: {stats.profit_factor:.2f}")
        print(f"  Max Profit: {stats.max_profit:,.2f}")
        print(f"  Max Loss: {stats.max_loss:,.2f}")
        
        print(f"\n[Risk Metrics]")
        print(f"  Sharpe Ratio: {stats.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {stats.max_drawdown:,.2f}")
        print(f"  Max DD %: {stats.max_drawdown_pct:.2f}%")
        
        print(f"\n[Equity Curve]")
        final_capital = self.initial_capital + stats.net_profit
        return_pct = (stats.net_profit / self.initial_capital) * 100
        print(f"  Initial Capital: {self.initial_capital:,.2f}")
        print(f"  Final Capital: {final_capital:,.2f}")
        print(f"  Total Return: {return_pct:.2f}%")
        
        print("="*70 + "\n")


def test_analyzer():
    """测试分析器"""
    analyzer = TradeAnalyzer(initial_capital=1_000_000)
    
    # 模拟一些交易记录
    base_time = datetime(2025, 2, 3, 9, 0, 0)
    
    # 交易1: 盈利
    analyzer.add_trade(TradeRecord(base_time, 'RU2505', 'LONG', 'OPEN', 15000, 1, 10))
    analyzer.add_trade(TradeRecord(base_time.replace(hour=10), 'RU2505', 'LONG', 'CLOSE', 15100, 1, 10))
    
    # 交易2: 亏损
    analyzer.add_trade(TradeRecord(base_time.replace(hour=11), 'RU2505', 'SHORT', 'OPEN', 15100, 1, 10))
    analyzer.add_trade(TradeRecord(base_time.replace(hour=14), 'RU2505', 'SHORT', 'CLOSE', 15150, 1, 10))
    
    # 交易3: 盈利
    analyzer.add_trade(TradeRecord(base_time.replace(day=4), 'RU2505', 'LONG', 'OPEN', 15100, 1, 10))
    analyzer.add_trade(TradeRecord(base_time.replace(day=4, hour=10), 'RU2505', 'LONG', 'CLOSE', 15200, 1, 10))
    
    stats = analyzer.analyze('RU2505', size=10)
    analyzer.print_report(stats)


if __name__ == "__main__":
    test_analyzer()
