#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多品种回测验证系统
支持批量回测、参数优化、报告生成
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional
import json

# Add project path
project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from strategies.macro_demo_strategy import MacroDemoStrategy, SYMBOL_CONFIG


@dataclass
class BacktestResult:
    """回测结果数据类"""
    symbol: str
    vt_symbol: str
    start_date: datetime
    end_date: datetime
    
    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # 盈亏统计
    total_profit: float
    total_loss: float
    net_profit: float
    profit_factor: float
    
    # 风险指标
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    
    # 资金曲线
    final_capital: float
    return_pct: float
    
    # 配置
    config: Dict


class MultiSymbolBacktester:
    """多品种回测器"""
    
    def __init__(self, capital: float = 1_000_000, mode: BacktestingMode = BacktestingMode.BAR):
        self.capital = capital
        self.mode = mode
        self.results: List[BacktestResult] = []
        
    def create_test_data(self, symbol: str, days: int = 30, 
                        trend: str = "mixed", start_price: float = 15000,
                        volatility: float = 0.02) -> List[BarData]:
        """
        创建更真实的测试K线数据
        
        Args:
            symbol: 品种代码
            days: 天数
            trend: 趋势类型 (up/down/mixed/range)
            start_price: 起始价格
            volatility: 波动率 (默认2%)
        """
        import random
        import math
        
        bars = []
        base_time = datetime(2025, 2, 3, 9, 0, 0)
        price = start_price
        
        # 获取品种配置
        config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        pricetick = config['pricetick']
        
        # 设置随机种子以便复现
        random.seed(42)
        
        # 趋势方向系数
        if trend == "up":
            trend_bias = 0.001  # 0.1% 向上偏移
        elif trend == "down":
            trend_bias = -0.001  # 0.1% 向下偏移
        elif trend == "range":
            trend_bias = 0.0
        else:  # mixed
            trend_bias = 0.0
        
        for day in range(days):
            # 每天的趋势变化
            if trend == "mixed":
                day_trend = math.sin(day * 0.3) * 0.002  # 周期性变化
            else:
                day_trend = trend_bias
            
            for minute in range(240):  # 每天240分钟
                # 生成价格变化
                change_pct = random.gauss(day_trend, volatility / math.sqrt(240))
                change = price * change_pct
                
                # 确保变化至少为一个pricetick
                if abs(change) < pricetick:
                    change = pricetick if change >= 0 else -pricetick
                
                # 更新价格
                new_price = price + change
                new_price = round(new_price / pricetick) * pricetick  # 对齐到pricetick
                new_price = max(new_price, pricetick * 10)  # 价格不能太低
                
                # 生成OHLC
                high_price = max(price, new_price) + random.uniform(0, pricetick * 3)
                low_price = min(price, new_price) - random.uniform(0, pricetick * 3)
                
                high_price = round(high_price / pricetick) * pricetick
                low_price = round(low_price / pricetick) * pricetick
                
                bar_time = base_time + timedelta(days=day, minutes=minute)
                bar = BarData(
                    symbol=f"{symbol}2505",
                    exchange=Exchange.SHFE,
                    datetime=bar_time,
                    open_price=price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=new_price,
                    volume=random.randint(50, 500),
                    open_interest=random.randint(1000, 5000),
                    gateway_name="BACKTESTING"
                )
                bars.append(bar)
                
                price = new_price
        
        return bars
    
    def run_single_backtest(self, symbol: str, vt_symbol: str,
                           start_date: datetime, end_date: datetime,
                           strategy_config: Dict,
                           test_data: Optional[List[BarData]] = None) -> BacktestResult:
        """
        运行单品种回测
        
        Args:
            symbol: 品种代码
            vt_symbol: 完整合约代码
            start_date: 开始日期
            end_date: 结束日期
            strategy_config: 策略配置
            test_data: 测试数据（可选）
        """
        engine = BacktestingEngine()
        
        # 获取品种配置
        sym_config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        
        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=Interval.MINUTE,
            start=start_date,
            end=end_date,
            rate=0.0001,
            slippage=sym_config['pricetick'],
            size=sym_config['size'],
            pricetick=sym_config['pricetick'],
            capital=self.capital,
            mode=self.mode
        )
        
        engine.add_strategy(MacroDemoStrategy, strategy_config)
        
        # 使用提供的测试数据或生成默认数据
        if test_data is None:
            test_data = self.create_test_data(symbol)
        
        engine.history_data = test_data
        engine.run_backtesting()
        
        # 计算统计指标
        trades = list(engine.trades.values())
        total_trades = len(trades)
        
        if total_trades == 0:
            return BacktestResult(
                symbol=symbol, vt_symbol=vt_symbol,
                start_date=start_date, end_date=end_date,
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_profit=0.0, total_loss=0.0,
                net_profit=0.0, profit_factor=0.0,
                max_drawdown=0.0, max_drawdown_pct=0.0,
                sharpe_ratio=0.0, final_capital=self.capital,
                return_pct=0.0, config=strategy_config
            )
        
        # 计算盈亏
        profits = [t.price * sym_config['size'] for t in trades if t.price > 0]
        losses = [t.price * sym_config['size'] for t in trades if t.price < 0]
        
        total_profit = sum(p for p in profits if p > 0)
        total_loss = abs(sum(l for l in losses if l < 0))
        net_profit = total_profit - total_loss
        
        winning_trades = len([t for t in trades if t.price > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 计算最大回撤（简化版）
        max_drawdown = 0.0
        peak = self.capital
        
        # 计算最终资金
        final_capital = self.capital + net_profit
        return_pct = (final_capital - self.capital) / self.capital * 100
        
        return BacktestResult(
            symbol=symbol, vt_symbol=vt_symbol,
            start_date=start_date, end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            final_capital=final_capital,
            return_pct=return_pct,
            config=strategy_config
        )
    
    def run_batch_backtest(self, symbols: List[str], 
                          strategy_configs: List[Dict],
                          start_date: datetime, end_date: datetime) -> List[BacktestResult]:
        """
        批量回测多个品种
        
        Args:
            symbols: 品种列表
            strategy_configs: 策略配置列表
            start_date: 开始日期
            end_date: 结束日期
        """
        results = []
        
        for symbol in symbols:
            for config in strategy_configs:
                # 构建合约代码
                exchange = SYMBOL_CONFIG.get(symbol, {}).get('exchange', 'SHFE')
                vt_symbol = f"{symbol}2505.{exchange}"
                
                print(f"\n回测: {vt_symbol}")
                print(f"配置: {config}")
                
                result = self.run_single_backtest(
                    symbol=symbol,
                    vt_symbol=vt_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_config=config
                )
                
                results.append(result)
                self.print_result(result)
        
        self.results = results
        return results
    
    def print_result(self, result: BacktestResult):
        """打印回测结果"""
        print(f"\n{'='*60}")
        print(f"回测结果: {result.vt_symbol}")
        print(f"{'='*60}")
        print(f"交易统计:")
        print(f"  总交易次数: {result.total_trades}")
        print(f"  盈利次数: {result.winning_trades}")
        print(f"  亏损次数: {result.losing_trades}")
        print(f"  胜率: {result.win_rate*100:.2f}%")
        print(f"\n盈亏统计:")
        print(f"  总盈利: {result.total_profit:.2f}")
        print(f"  总亏损: {result.total_loss:.2f}")
        print(f"  净利润: {result.net_profit:.2f}")
        print(f"  盈亏比: {result.profit_factor:.2f}")
        print(f"\n资金曲线:")
        print(f"  初始资金: {self.capital:.2f}")
        print(f"  最终资金: {result.final_capital:.2f}")
        print(f"  收益率: {result.return_pct:.2f}%")
        print(f"{'='*60}\n")
    
    def generate_report(self, output_path: str = "backtest_report.json"):
        """生成回测报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "capital": self.capital,
            "total_results": len(self.results),
            "results": []
        }
        
        for result in self.results:
            report["results"].append({
                "symbol": result.symbol,
                "vt_symbol": result.vt_symbol,
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "net_profit": result.net_profit,
                "profit_factor": result.profit_factor,
                "return_pct": result.return_pct,
                "config": result.config
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"报告已保存: {output_path}")


def test_single_symbol():
    """测试单品种回测"""
    print("="*60)
    print("单品种回测测试")
    print("="*60)
    
    backtester = MultiSymbolBacktester(capital=1_000_000)
    
    # 保守配置
    conservative_config = {
        'fast_window': 10,
        'slow_window': 20,
        'use_macro': False,
        'enable_stop_loss': True,
        'enable_take_profit': True,
        'enable_trailing_stop': True,
        'enable_tech_exit': True,
        'stop_loss': 50,
        'take_profit': 100,
        'trailing_stop': 30
    }
    
    # 测试上涨趋势
    print("\n--- 上涨趋势测试 ---")
    up_data = backtester.create_test_data('RU', days=10, trend='up', start_price=15000)
    result = backtester.run_single_backtest(
        symbol='RU',
        vt_symbol='RU2505.SHFE',
        start_date=datetime(2025, 2, 3),
        end_date=datetime(2025, 2, 13),
        strategy_config=conservative_config,
        test_data=up_data
    )
    backtester.print_result(result)
    
    # 测试下跌趋势
    print("\n--- 下跌趋势测试 ---")
    down_data = backtester.create_test_data('RU', days=10, trend='down', start_price=15000)
    result = backtester.run_single_backtest(
        symbol='RU',
        vt_symbol='RU2505.SHFE',
        start_date=datetime(2025, 2, 3),
        end_date=datetime(2025, 2, 13),
        strategy_config=conservative_config,
        test_data=down_data
    )
    backtester.print_result(result)
    
    # 测试震荡趋势
    print("\n--- 震荡趋势测试 ---")
    range_data = backtester.create_test_data('RU', days=10, trend='range', start_price=15000)
    result = backtester.run_single_backtest(
        symbol='RU',
        vt_symbol='RU2505.SHFE',
        start_date=datetime(2025, 2, 3),
        end_date=datetime(2025, 2, 13),
        strategy_config=conservative_config,
        test_data=range_data
    )
    backtester.print_result(result)


def test_multi_symbol():
    """测试多品种回测"""
    print("\n" + "="*60)
    print("多品种回测测试")
    print("="*60)
    
    backtester = MultiSymbolBacktester(capital=1_000_000)
    
    # 测试品种
    symbols = ['RU', 'ZN', 'RB']
    
    # 不同配置
    configs = [
        {
            'name': '保守配置',
            'fast_window': 10,
            'slow_window': 20,
            'use_macro': False,
            'enable_stop_loss': True,
            'enable_take_profit': True,
            'enable_trailing_stop': False,
            'enable_tech_exit': False,
            'stop_loss': 50,
            'take_profit': 100
        },
        {
            'name': '激进配置',
            'fast_window': 5,
            'slow_window': 10,
            'use_macro': False,
            'enable_stop_loss': True,
            'enable_take_profit': False,
            'enable_trailing_stop': False,
            'enable_tech_exit': True,
            'stop_loss': 100
        }
    ]
    
    results = backtester.run_batch_backtest(
        symbols=symbols,
        strategy_configs=configs,
        start_date=datetime(2025, 2, 3),
        end_date=datetime(2025, 2, 13)
    )
    
    # 生成报告
    backtester.generate_report("D:/futures_v6/backtest_report.json")


if __name__ == "__main__":
    test_single_symbol()
    test_multi_symbol()
    print("\n回测测试完成！")
