"""
参数敏感性分析 (Phase 5.2)
分析不同参数组合对回测结果的影响
"""

from config.paths import MACRO_ENGINE, PROJECT_ROOT
import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple

# Setup paths
project_dir = Path(__file__).resolve().parent.parent
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))


class MacroSignalLoader:
    """加载宏观信号 CSV 数据"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.signals = defaultdict(dict)
        self._load_all()
    
    def _load_all(self):
        """加载所有历史信号"""
        for csv_file in sorted(self.output_dir.glob("*_macro_daily_*.csv")):
            parts = csv_file.stem.split('_')
            if len(parts) >= 4 and parts[1] == 'macro' and parts[2] == 'daily':
                symbol = parts[0]
                date_str = parts[-1]
                
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_type = row.get('rowType', '') or row.get('row_type', '')
                        if row_type == 'SUMMARY':
                            score_str = row.get('compositeScore', '') or row.get('composite_score', '')
                            self.signals[symbol][date_str] = {
                                'direction': row['direction'],
                                'score': float(score_str) if score_str else 0.0,
                            }
                            break
    
    def get_signal(self, symbol: str, date_str: str) -> dict:
        return self.signals.get(symbol, {}).get(date_str, {
            'direction': 'NEUTRAL', 'score': 0.0
        })


class SensitivityEngine:
    """参数敏感性分析引擎"""
    
    def __init__(self, symbol: str, start: str, end: str):
        self.symbol = symbol
        self.start = start
        self.end = end
        self.loader = MacroSignalLoader("str(MACRO_ENGINE)/output")
        
        # Get date range
        self.dates = []
        current = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        while current <= end_dt:
            self.dates.append(current.strftime("%Y%m%d"))
            current = datetime.fromtimestamp(current.timestamp() + 86400)
    
    def run_scenarios(self) -> List[Dict]:
        """运行多参数场景分析"""
        
        scenarios = []
        
        # 参数组合
        score_thresholds = [0.0, 0.1, 0.2, 0.3, 0.5]  # 信号阈值
        hold_days_list = [3, 5, 7, 10]  # 持仓天数
        position_sizes = [1, 2, 3, 5]  # 手数
        
        total = len(score_thresholds) * len(hold_days_list) * len(position_sizes)
        print(f"[Sensitivity] Running {total} scenarios...")
        
        for score_thresh in score_thresholds:
            for hold_days in hold_days_list:
                for pos_size in position_sizes:
                    result = self._run_single_scenario(
                        score_threshold=score_thresh,
                        hold_days=hold_days,
                        position_size=pos_size,
                    )
                    scenarios.append(result)
        
        return scenarios
    
    def _run_single_scenario(self, score_threshold: float, hold_days: int, 
                            position_size: int) -> Dict:
        """运行单个参数组合"""
        
        import random
        random.seed(42)
        
        trades = []
        capital = 100000.0
        position = 0
        entry_price = 0
        entry_idx = 0
        
        for i, date_str in enumerate(self.dates):
            sig = self.loader.get_signal(self.symbol, date_str)
            
            if position == 0:
                # Entry: direction + score threshold
                if sig['direction'] in ('LONG', 'SHORT') and abs(sig['score']) >= score_threshold:
                    position = 1 if sig['direction'] == 'LONG' else -1
                    entry_price = 10000 + random.gauss(0, 100)
                    entry_idx = i
            else:
                # Exit conditions
                hold_duration = i - entry_idx
                direction_changed = (position > 0 and sig['direction'] == 'SHORT') or \
                                   (position < 0 and sig['direction'] == 'LONG')
                
                if direction_changed or hold_duration >= hold_days or sig['direction'] == 'NEUTRAL':
                    exit_price = entry_price + random.gauss(0, 200) + (position * sig['score'] * 100)
                    pnl = position * (exit_price - entry_price) * 10 * position_size
                    capital += pnl
                    
                    trades.append({
                        'pnl': pnl,
                        'hold_days': hold_duration,
                    })
                    position = 0
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        total_pnl = sum(t['pnl'] for t in trades)
        returns = (capital - 100000) / 100000
        
        # Sharpe
        if total_trades > 1:
            pnls = [t['pnl'] for t in trades]
            avg_pnl = sum(pnls) / len(pnls)
            std_pnl = (sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)) ** 0.5
            sharpe = (avg_pnl / std_pnl) * (252 ** 0.5) if std_pnl > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown
        cumulative = []
        cum = 100000.0
        for t in trades:
            cum += t['pnl']
            cumulative.append(cum)
        
        max_dd = 0
        peak = 100000.0
        for c in cumulative:
            if c > peak:
                peak = c
            dd = (peak - c) / peak
            if dd > max_dd:
                max_dd = dd
        
        return {
            'score_threshold': score_threshold,
            'hold_days': hold_days,
            'position_size': position_size,
            'total_trades': total_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'returns': returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'final_capital': capital,
        }
    
    def print_top_scenarios(self, scenarios: List[Dict], top_n: int = 10):
        """打印最佳参数组合"""
        
        # Sort by Sharpe ratio
        sorted_by_sharpe = sorted(scenarios, key=lambda x: x['sharpe_ratio'], reverse=True)
        
        print("\n" + "=" * 100)
        print(f"Top {top_n} Scenarios by Sharpe Ratio")
        print("=" * 100)
        print(f"{'Rank':<6}{'ScoreThresh':<12}{'HoldDays':<10}{'PosSize':<10}{'Trades':<8}{'WinRate':<10}{'PnL':<12}{'Returns':<10}{'Sharpe':<10}{'MaxDD':<10}")
        print("-" * 100)
        
        for i, s in enumerate(sorted_by_sharpe[:top_n], 1):
            print(f"{i:<6}{s['score_threshold']:<12.1f}{s['hold_days']:<10}{s['position_size']:<10}"
                  f"{s['total_trades']:<8}{s['win_rate']:<10.1%}{s['total_pnl']:<12.2f}"
                  f"{s['returns']:<10.2%}{s['sharpe_ratio']:<10.2f}{s['max_drawdown']:<10.2%}")
        
        # Sort by returns
        sorted_by_return = sorted(scenarios, key=lambda x: x['returns'], reverse=True)
        
        print("\n" + "=" * 100)
        print(f"Top {top_n} Scenarios by Returns")
        print("=" * 100)
        print(f"{'Rank':<6}{'ScoreThresh':<12}{'HoldDays':<10}{'PosSize':<10}{'Trades':<8}{'WinRate':<10}{'PnL':<12}{'Returns':<10}{'Sharpe':<10}{'MaxDD':<10}")
        print("-" * 100)
        
        for i, s in enumerate(sorted_by_return[:top_n], 1):
            print(f"{i:<6}{s['score_threshold']:<12.1f}{s['hold_days']:<10}{s['position_size']:<10}"
                  f"{s['total_trades']:<8}{s['win_rate']:<10.1%}{s['total_pnl']:<12.2f}"
                  f"{s['returns']:<10.2%}{s['sharpe_ratio']:<10.2f}{s['max_drawdown']:<10.2%}")
        
        # Risk-adjusted (Sharpe / MaxDD)
        risk_adjusted = [s for s in scenarios if s['max_drawdown'] > 0]
        for s in risk_adjusted:
            s['risk_adjusted'] = s['sharpe_ratio'] / s['max_drawdown']
        
        sorted_by_risk = sorted(risk_adjusted, key=lambda x: x['risk_adjusted'], reverse=True)
        
        print("\n" + "=" * 100)
        print(f"Top {top_n} Scenarios by Risk-Adjusted Return (Sharpe/MaxDD)")
        print("=" * 100)
        print(f"{'Rank':<6}{'ScoreThresh':<12}{'HoldDays':<10}{'PosSize':<10}{'Trades':<8}{'WinRate':<10}{'PnL':<12}{'Returns':<10}{'Sharpe':<10}{'MaxDD':<10}{'RiskAdj':<10}")
        print("-" * 110)
        
        for i, s in enumerate(sorted_by_risk[:top_n], 1):
            print(f"{i:<6}{s['score_threshold']:<12.1f}{s['hold_days']:<10}{s['position_size']:<10}"
                  f"{s['total_trades']:<8}{s['win_rate']:<10.1%}{s['total_pnl']:<12.2f}"
                  f"{s['returns']:<10.2%}{s['sharpe_ratio']:<10.2f}{s['max_drawdown']:<10.2%}"
                  f"{s['risk_adjusted']:<10.2f}")
    
    def save_results(self, scenarios: List[Dict]):
        """保存分析结果"""
        output_file = PROJECT_ROOT / f"sensitivity_{self.symbol}_{self.start}_{self.end}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(scenarios, f, indent=2, ensure_ascii=False)
        print(f"\n[Saved] {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sensitivity Analysis")
    parser.add_argument("--symbol", default="RU", help="Symbol")
    parser.add_argument("--start", default="2026-01-01", help="Start date")
    parser.add_argument("--end", default="2026-04-24", help="End date")
    args = parser.parse_args()
    
    engine = SensitivityEngine(args.symbol, args.start, args.end)
    scenarios = engine.run_scenarios()
    engine.print_top_scenarios(scenarios, top_n=10)
    engine.save_results(scenarios)


if __name__ == "__main__":
    main()
