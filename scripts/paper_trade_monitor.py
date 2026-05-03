"""
模拟盘连续运行监控 (Phase 5.3)
解决零成交问题，使用优化参数进行模拟盘测试
"""

from config.paths import MACRO_ENGINE, PROJECT_ROOT
import os
import sys
import csv
import json
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Setup paths
project_dir = Path(__file__).resolve().parent.parent
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))
sys.path.insert(0, str(project_dir / "strategies"))


class PaperTradeEngine:
    """模拟盘交易引擎"""
    
    def __init__(self, symbol: str, capital: float = 100000.0):
        self.symbol = symbol
        self.capital = capital
        self.initial_capital = capital
        
        # 优化参数（来自敏感性分析）
        self.params = self._get_optimized_params(symbol)
        
        # 交易状态
        self.position = 0  # 0=空仓, 1=多仓, -1=空仓
        self.entry_price = 0.0
        self.entry_date = None
        self.trades = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # 风控参数
        self.max_daily_loss = 5000.0
        self.max_position = 10
        self.max_daily_trades = 20
        
        # 加载信号
        self.signal_loader = self._load_signals()
        
        print(f"[PaperTrade] {symbol} | Capital: {capital:,.2f}")
        print(f"[PaperTrade] Params: {self.params}")
    
    def _get_optimized_params(self, symbol: str) -> dict:
        """获取优化参数"""
        params_map = {
            'AU': {'score_threshold': 0.3, 'hold_days': 3, 'position_size': 1},
            'CU': {'score_threshold': 0.2, 'hold_days': 3, 'position_size': 1},
            'AG': {'score_threshold': 0.3, 'hold_days': 3, 'position_size': 1},
            'RU': {'score_threshold': 0.3, 'hold_days': 3, 'position_size': 1},
        }
        return params_map.get(symbol, {'score_threshold': 0.3, 'hold_days': 3, 'position_size': 1})
    
    def _load_signals(self) -> dict:
        """加载历史信号"""
        signals = {}
        output_dir = Path("str(MACRO_ENGINE)/output")
        
        for csv_file in sorted(output_dir.glob(f"{self.symbol}_macro_daily_*.csv")):
            date_str = csv_file.stem.split('_')[-1]
            
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_type = row.get('rowType', '') or row.get('row_type', '')
                    if row_type == 'SUMMARY':
                        score_str = row.get('compositeScore', '') or row.get('composite_score', '')
                        signals[date_str] = {
                            'direction': row['direction'],
                            'score': float(score_str) if score_str else 0.0,
                        }
                        break
        
        print(f"[PaperTrade] Loaded {len(signals)} signals for {self.symbol}")
        return signals
    
    def get_signal(self, date_str: str) -> dict:
        """获取某日期信号"""
        return self.signal_loader.get(date_str, {
            'direction': 'NEUTRAL',
            'score': 0.0,
        })
    
    def simulate_price(self, base_price: float = 10000.0) -> float:
        """模拟价格（实际应连接行情）"""
        return base_price + random.gauss(0, 50)
    
    def check_risk(self, action: str, price: float, volume: int) -> bool:
        """风控检查"""
        # 1. 单日最大亏损
        if self.daily_pnl < -self.max_daily_loss:
            print(f"[Risk] Daily loss limit reached: {self.daily_pnl:.2f}")
            return False
        
        # 2. 最大持仓
        if action == 'OPEN':
            new_position = self.position + (1 if volume > 0 else -1)
            if abs(new_position) > self.max_position:
                print(f"[Risk] Position limit: {abs(new_position)} > {self.max_position}")
                return False
        
        # 3. 单日交易次数
        if self.daily_trades >= self.max_daily_trades:
            print(f"[Risk] Daily trade limit reached")
            return False
        
        return True
    
    def execute_trade(self, date_str: str, action: str, direction: str, 
                     price: float, volume: int, score: float = 0.0):
        """执行交易"""
        if not self.check_risk(action, price, volume):
            return False
        
        if action == 'OPEN':
            self.position = 1 if direction == 'LONG' else -1
            self.entry_price = price
            self.entry_date = date_str
            
            self.trades.append({
                'date': date_str,
                'action': 'OPEN',
                'direction': direction,
                'price': price,
                'volume': volume,
                'score': score,
            })
            
            print(f"[Trade] OPEN {direction} {volume}@{price:.2f} (score={score:.3f})")
            
        elif action == 'CLOSE':
            pnl = self.position * (price - self.entry_price) * 10 * volume
            self.capital += pnl
            self.daily_pnl += pnl
            
            hold_days = (datetime.strptime(date_str, "%Y%m%d") - 
                        datetime.strptime(self.entry_date, "%Y%m%d")).days
            
            self.trades.append({
                'date': date_str,
                'action': 'CLOSE',
                'direction': 'LONG' if self.position > 0 else 'SHORT',
                'price': price,
                'volume': volume,
                'pnl': pnl,
                'hold_days': hold_days,
                'capital': self.capital,
            })
            
            print(f"[Trade] CLOSE {volume}@{price:.2f} PnL={pnl:+.2f} Capital={self.capital:,.2f}")
            
            self.position = 0
            self.entry_price = 0.0
            self.entry_date = None
        
        self.daily_trades += 1
        return True
    
    def run_simulation(self, start_date: str, end_date: str):
        """运行模拟"""
        print(f"\n[Simulation] {self.symbol} | {start_date} ~ {end_date}")
        print("=" * 60)
        
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        days_processed = 0
        
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            sig = self.get_signal(date_str)
            
            # 重置日度计数器
            self.daily_pnl = 0.0
            self.daily_trades = 0
            
            if sig['direction'] != 'NEUTRAL' or sig['score'] != 0.0:
                price = self.simulate_price()
                
                if self.position == 0:
                    # 开仓条件：信号方向 + 阈值
                    if abs(sig['score']) >= self.params['score_threshold']:
                        direction = sig['direction']
                        volume = self.params['position_size']
                        self.execute_trade(date_str, 'OPEN', direction, price, volume, sig['score'])
                
                else:
                    # 平仓条件
                    hold_days = 0
                    if self.entry_date:
                        hold_days = (current - datetime.strptime(self.entry_date, "%Y%m%d")).days
                    
                    direction_changed = (self.position > 0 and sig['direction'] == 'SHORT') or \
                                       (self.position < 0 and sig['direction'] == 'LONG')
                    
                    if direction_changed or hold_days >= self.params['hold_days']:
                        volume = self.params['position_size']
                        self.execute_trade(date_str, 'CLOSE', '', price, volume)
            
            current += timedelta(days=1)
            days_processed += 1
            
            if days_processed % 30 == 0:
                print(f"[Progress] {days_processed} days processed, Capital: {self.capital:,.2f}")
        
        self._print_summary()
    
    def _print_summary(self):
        """打印汇总"""
        closed_trades = [t for t in self.trades if t['action'] == 'CLOSE']
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t.get('pnl', 0) > 0])
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        returns = (self.capital - self.initial_capital) / self.initial_capital
        
        print("\n" + "=" * 60)
        print("Paper Trade Summary")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {winning_trades}")
        print(f"Win Rate: {winning_trades/total_trades:.1%}" if total_trades > 0 else "N/A")
        print(f"Total PnL: {total_pnl:+.2f}")
        print(f"Final Capital: {self.capital:,.2f}")
        print(f"Returns: {returns:+.2%}")
        print("=" * 60)
    
    def save_results(self, filename: str = None):
        """保存结果"""
        if filename is None:
            filename = f"paper_trade_{self.symbol}_{datetime.now().strftime('%Y%m%d')}.json"
        
        output_file = PROJECT_ROOT / filename
        results = {
            'symbol': self.symbol,
            'params': self.params,
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'returns': (self.capital - self.initial_capital) / self.initial_capital,
            'trades': self.trades,
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"[Saved] {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Paper Trade Monitor")
    parser.add_argument("--symbol", default="AU", help="Symbol to trade")
    parser.add_argument("--start", default="2026-01-01", help="Start date")
    parser.add_argument("--end", default="2026-04-24", help="End date")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial capital")
    args = parser.parse_args()
    
    engine = PaperTradeEngine(args.symbol, args.capital)
    engine.run_simulation(args.start, args.end)
    engine.save_results()


if __name__ == "__main__":
    main()
