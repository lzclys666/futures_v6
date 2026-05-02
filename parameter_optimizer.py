#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parameter Optimization System - Grid Search for Best Configurations
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import json
import itertools

# Add project path
project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from production_backtest import ProductionBacktester, BacktestResult


class ParameterOptimizer:
    """参数优化器 - 网格搜索最优参数组合"""
    
    def __init__(self, capital: float = 1_000_000):
        self.backtester = ProductionBacktester(capital=capital)
        self.results: List[Tuple[Dict, BacktestResult]] = []
        
    def generate_configs(self, param_grid: Dict) -> List[Dict]:
        """
        生成参数组合
        
        Args:
            param_grid: 参数网格，例如：
                {
                    'fast_window': [5, 10, 15],
                    'slow_window': [20, 30, 40],
                    'stop_loss': [3000, 5000, 8000]
                }
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        configs = []
        for combo in itertools.product(*values):
            config = dict(zip(keys, combo))
            config['name'] = f"grid_{'_'.join([f'{k}={v}' for k, v in config.items()])}"
            configs.append(config)
        
        return configs
    
    def optimize(self, symbol: str, param_grid: Dict, 
                 data=None, days: int = 10,
                 metric: str = 'sharpe_ratio') -> Tuple[Dict, BacktestResult]:
        """
        执行参数优化
        
        Args:
            symbol: 品种代码
            param_grid: 参数网格
            data: 预生成的数据（可选）
            days: 回测天数
            metric: 优化目标指标 ('sharpe_ratio', 'net_profit', 'win_rate', 'profit_factor')
        """
        print(f"\n{'='*70}")
        print(f"Parameter Optimization: {symbol}")
        print(f"Target Metric: {metric}")
        print(f"{'='*70}")
        
        # 生成参数组合
        configs = self.generate_configs(param_grid)
        print(f"Total combinations: {len(configs)}")
        
        # 预生成数据
        if data is None:
            data = self.backtester.create_realistic_data(symbol, days=days)
        
        # 运行所有组合
        best_config = None
        best_result = None
        best_score = float('-inf')
        
        for i, config in enumerate(configs):
            print(f"\n[{i+1}/{len(configs)}] Testing: {config['name']}")
            
            # 添加固定参数
            full_config = {
                **config,
                'use_macro': False,
                'enable_stop_loss': True,
                'enable_take_profit': True,
                'enable_trailing_stop': False,
                'enable_tech_exit': True,
                'take_profit': 10000
            }
            
            result = self.backtester.run_backtest(symbol, full_config, data=data)
            self.results.append((config, result))
            
            # 获取评分
            score = getattr(result, metric, 0)
            print(f"  Score ({metric}): {score:.4f}")
            
            if score > best_score:
                best_score = score
                best_config = config
                best_result = result
                print(f"  *** New Best! ***")
        
        print(f"\n{'='*70}")
        print(f"Optimization Complete!")
        print(f"Best Config: {best_config}")
        print(f"Best {metric}: {best_score:.4f}")
        print(f"{'='*70}")
        
        return best_config, best_result
    
    def print_top_results(self, n: int = 10, metric: str = 'sharpe_ratio'):
        """打印前N个最佳结果"""
        sorted_results = sorted(
            self.results, 
            key=lambda x: getattr(x[1], metric, 0), 
            reverse=True
        )
        
        print(f"\n{'='*70}")
        print(f"Top {n} Results (by {metric})")
        print(f"{'='*70}")
        
        for i, (config, result) in enumerate(sorted_results[:n]):
            print(f"\n#{i+1}: {config['name']}")
            print(f"  Win Rate: {result.win_rate*100:.2f}%")
            print(f"  Net Profit: {result.net_profit:,.2f}")
            print(f"  Profit Factor: {result.profit_factor:.2f}")
            print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"  Max DD: {result.max_drawdown_pct:.2f}%")
    
    def save_results(self, output_path: str = "optimization_results.json"):
        """保存优化结果"""
        results = []
        for config, result in self.results:
            results.append({
                'config': config,
                'win_rate': result.win_rate,
                'net_profit': result.net_profit,
                'profit_factor': result.profit_factor,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown_pct': result.max_drawdown_pct,
                'return_pct': result.return_pct
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved: {output_path}")


def run_optimization_demo():
    """运行参数优化示例"""
    
    # 定义参数网格
    param_grid = {
        'fast_window': [5, 10, 15],
        'slow_window': [20, 30, 40],
        'stop_loss': [3000, 5000, 8000]
    }
    
    optimizer = ParameterOptimizer(capital=1_000_000)
    
    # 优化RU品种
    best_config, best_result = optimizer.optimize(
        symbol='RU',
        param_grid=param_grid,
        days=10,
        metric='sharpe_ratio'
    )
    
    # 打印前10结果
    optimizer.print_top_results(n=10, metric='sharpe_ratio')
    
    # 保存结果
    optimizer.save_results("D:/futures_v6/optimization_results.json")
    
    print("\n" + "="*70)
    print("Optimization Demo Complete!")
    print("="*70)


if __name__ == "__main__":
    run_optimization_demo()
