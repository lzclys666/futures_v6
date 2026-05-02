#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号驱动回测系统
- 用真实 CSV 宏观信号驱动
- 使用 MacroRiskStrategy + RiskEngine
- 每日趋势匹配信号方向
- 完整统计：夏普、最大回撤、胜率、盈亏比
"""

import sys
import os
import math
import random
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import csv

sys.path.insert(0, r'D:\futures_v6')

from vnpy.trader.constant import Interval, Exchange, Direction, Status
from vnpy.trader.object import BarData

# Import strategy config
from strategies.macro_risk_strategy import SYMBOL_CONFIG
from core.risk.risk_engine import RiskContext, OrderRequest, RiskAction


# ============================================================
# Data Classes
# ============================================================

@dataclass
class SignalRecord:
    """每日信号记录"""
    date: str
    symbol: str
    direction: str    # LONG / SHORT / NEUTRAL
    score: float
    confidence: str   # HIGH / MEDIUM / LOW


@dataclass
class CompletedTrade:
    """已完成交易"""
    symbol: str
    open_dt: datetime
    close_dt: datetime
    direction: str
    open_price: float
    close_price: float
    volume: int
    size: int
    pnl: float
    pnl_pct: float
    risk_blocked: bool = False


@dataclass
class DailyEquity:
    """每日权益"""
    date: str
    equity: float
    pnl: float
    position: int


@dataclass
class BacktestReport:
    """完整回测报告"""
    symbol: str
    start_date: str
    end_date: str
    total_days: int
    initial_capital: float
    final_capital: float
    return_pct: float
    annualized_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_profit: float
    max_loss: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    signal_accuracy: float  # 信号方向是否正确
    trades: List[CompletedTrade] = field(default_factory=list)
    equity_curve: List[DailyEquity] = field(default_factory=list)


# ============================================================
# Data Generator
# ============================================================

class TrendBarGenerator:
    """趋势匹配的 Bar 生成器 - 每日趋势方向跟随 CSV 信号"""

    BASE_PRICES = {
        'RU': 15000, 'ZN': 22000, 'RB': 3500, 'NI': 130000,
        'CU': 70000, 'AU': 480, 'AG': 5800, 'NR': 11000,
        'TA': 5800, 'SA': 1800, 'BR': 10000,
    }

    def __init__(self, years_back: int = 0):
        self.rng = random.Random(42)
        self.years_back = years_back

    def generate_day_bars(self, symbol: str, date_str: str,
                          signal_direction: str,
                          volatility: float = 0.015) -> List[BarData]:
        """
        生成一天（240分钟）的 1 分钟 K 线
        trend 跟随 signal_direction:
        - LONG: 向上趋势
        - SHORT: 向下趋势
        - NEUTRAL: 震荡
        """
        config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        pricetick = config['pricetick']
        base_price = self.BASE_PRICES.get(symbol, 15000)

        # 解析日期
        y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
        day_dt = datetime(y, m, d, 9, 0, 0)

        # 跳过周末
        if day_dt.weekday() >= 5:
            return []

        # 趋势偏置
        if signal_direction == 'LONG':
            trend_bias = 0.0003 + self.rng.uniform(0, 0.0002)
        elif signal_direction == 'SHORT':
            trend_bias = -0.0003 - self.rng.uniform(0, 0.0002)
        else:
            trend_bias = 0.0

        bars = []
        price = base_price + self.rng.uniform(-500, 500)

        # 添加开盘跳空
        gap = self.rng.gauss(0, volatility * 0.3)
        price += price * gap

        for minute in range(240):
            hour = 9 + (minute // 60)
            actual_minute = minute % 60
            t = day_dt.replace(hour=hour, minute=actual_minute)

            # 午间休市 11:30-13:00
            if (hour == 11 and actual_minute > 30) or (hour == 12):
                continue

            # 时间因子：开盘30分钟和收盘30分钟波动更大
            time_factor = 1.0
            if minute < 30:
                time_factor = 1.3
            elif minute > 210:
                time_factor = 1.2

            # 随机游走 + 趋势
            change_pct = self.rng.gauss(trend_bias, volatility * time_factor / math.sqrt(240))
            change = price * change_pct

            if abs(change) < pricetick:
                change = pricetick * (1 if self.rng.random() > 0.5 else -1)

            new_price = price + change
            new_price = round(new_price / pricetick) * pricetick
            new_price = max(new_price, pricetick * 100)

            # OHLC
            high = max(price, new_price) + abs(self.rng.gauss(0, volatility * price * 0.15))
            low = min(price, new_price) - abs(self.rng.gauss(0, volatility * price * 0.15))
            high = round(high / pricetick) * pricetick
            low = round(low / pricetick) * pricetick

            bar = BarData(
                symbol=f"{symbol}99",
                exchange=Exchange.SHFE,
                datetime=t,
                open_price=price,
                high_price=high,
                low_price=low,
                close_price=new_price,
                volume=self.rng.randint(50, 500),
                open_interest=self.rng.randint(5000, 50000),
                gateway_name="BACKTEST"
            )
            bars.append(bar)
            price = new_price

        # 收盘价相对开盘价: 匹配信号方向
        if bars and signal_direction != 'NEUTRAL':
            open_p = bars[0].open_price
            close_p = bars[-1].close_price
            expected_up = signal_direction == 'LONG'
            if expected_up and close_p <= open_p:
                bars[-1].close_price = open_p * 1.005
            elif not expected_up and close_p >= open_p:
                bars[-1].close_price = open_p * 0.995

        return bars


# ============================================================
# Signal Loader
# ============================================================

class SignalLoader:
    """CSV 信号加载器"""

    def __init__(self, signal_dir: str = r'D:\futures_v6\macro_engine\output'):
        self.signal_dir = signal_dir

    def get_all_dates(self) -> List[str]:
        """获取所有可用日期（去重排序）"""
        dates = set()
        for f in os.listdir(self.signal_dir):
            if f.endswith('.csv'):
                parts = f.replace('.csv', '').split('_macro_daily_')
                if len(parts) == 2:
                    dates.add(parts[1])
        return sorted(dates)

    def get_available_symbols(self) -> List[str]:
        """获取可用品种列表"""
        symbols = set()
        for f in os.listdir(self.signal_dir):
            if f.endswith('.csv'):
                sym = f.split('_')[0]
                symbols.add(sym)
        # 过滤合并文件名
        clean = set()
        for s in symbols:
            if ',' not in s:
                clean.add(s)
        return sorted(clean)

    def load_signal(self, symbol: str, date_str: str) -> Optional[SignalRecord]:
        """加载某天某品种的信号"""
        fname = f'{symbol}_macro_daily_{date_str}.csv'
        fpath = os.path.join(self.signal_dir, fname)

        if not os.path.exists(fpath):
            return None

        try:
            with open(fpath, 'r', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    row_type = row.get('row_type', '') or row.get('rowType', '')
                    if row_type == 'SUMMARY' and row.get('symbol', '') == symbol:
                        return SignalRecord(
                            date=date_str,
                            symbol=symbol,
                            direction=str(row.get('direction', 'NEUTRAL')).upper(),
                            score=float(row.get('composite_score', 50)),
                            confidence=str(row.get('confidence', 'MEDIUM')).upper()
                        )
        except Exception:
            pass
        return None

    def load_all_signals(self, symbol: str) -> Dict[str, SignalRecord]:
        """加载某个品种的所有信号"""
        signals = {}
        for date_str in self.get_all_dates():
            sig = self.load_signal(symbol, date_str)
            if sig:
                signals[date_str] = sig
        return signals


# ============================================================
# Backtesting Engine
# ============================================================

class SignalDrivenBacktester:
    """信号驱动的回测引擎"""

    def __init__(self, capital: float = 1_000_000, risk_profile: str = "moderate"):
        self.initial_capital = capital
        self.capital = capital
        self.risk_profile = risk_profile
        self.signal_loader = SignalLoader()
        self.bar_gen = TrendBarGenerator()

        # 交易记录
        self.trades: List[CompletedTrade] = []
        self.positions: Dict[str, Dict] = {}  # symbol -> {direction, price, volume}
        self.equity_curve: List[DailyEquity] = []

        # RiskEngine (lazy init)
        self.risk_engine = None

    def _init_risk_engine(self):
        if self.risk_engine is None:
            from core.risk.risk_engine import RiskEngine
            self.risk_engine = RiskEngine(profile=self.risk_profile)
            print(f"  RiskEngine: {self.risk_profile}, "
                  f"{len([r for r in self.risk_engine.rules if r.is_enabled()])} active rules")

    def _is_trading_date(self, date_str: str) -> bool:
        """判断是否交易日（周一到周五）"""
        y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
        return datetime(y, m, d).weekday() < 5

    def run(self, symbol: str, days: int = 30) -> BacktestReport:
        """运行回测"""
        print(f"\n{'='*70}")
        print(f"Signal-Driven Backtest: {symbol}")
        print(f"  Capital: {self.initial_capital:,.0f}")
        print(f"  Risk Profile: {self.risk_profile}")
        print(f"{'='*70}")

        self._init_risk_engine()
        config = SYMBOL_CONFIG.get(symbol, {'size': 10, 'pricetick': 1})
        size = config['size']
        pricetick = config['pricetick']

        # 加载信号
        all_signals = self.signal_loader.load_all_signals(symbol)
        dates = sorted(all_signals.keys())
        if days > 0:
            dates = dates[-days:]

        # 过滤交易日
        trading_dates = [d for d in dates if self._is_trading_date(d)]
        if not trading_dates:
            print(f"  No trading dates found for {symbol}")
            return self._empty_report(symbol)

        print(f"  Data: {len(trading_dates)} trading days")
        print(f"  Range: {trading_dates[0]} - {trading_dates[-1]}")

        # 逐日回测
        for date_str in trading_dates:
            self._process_day(symbol, date_str, all_signals[date_str], config)

        # 生成报告
        return self._generate_report(symbol, trading_dates)

    def _process_day(self, symbol: str, date_str: str,
                     signal: SignalRecord, config: dict):
        """处理一天的回测"""

        size = config['size']

        # 1. 生成当日 bars
        bars = self.bar_gen.generate_day_bars(symbol, date_str, signal.direction)
        if not bars:
            return

        open_price = bars[0].open_price
        close_price = bars[-1].close_price

        # 2. 检查是否有持仓需要平仓（持仓超过1天自动平仓）
        if symbol in self.positions:
            pos = self.positions[symbol]
            # 平仓价格 = 当日收盘价
            exit_price = close_price
            if pos['direction'] == 'LONG':
                pnl = (exit_price - pos['price']) * pos['volume'] * size
            else:
                pnl = (pos['price'] - exit_price) * pos['volume'] * size

            trade = CompletedTrade(
                symbol=symbol,
                open_dt=pos['open_dt'],
                close_dt=bars[-1].datetime,
                direction=pos['direction'],
                open_price=pos['price'],
                close_price=exit_price,
                volume=pos['volume'],
                size=size,
                pnl=pnl,
                pnl_pct=pnl / self.capital * 100,
                risk_blocked=False
            )
            self.trades.append(trade)
            self.capital += pnl
            del self.positions[symbol]

        # 3. 根据信号决定是否开仓
        if signal.direction == 'NEUTRAL':
            return

        # 4. 风控检查（Layer 1/2/3）
        if self.risk_engine:
            order = OrderRequest(
                symbol=symbol,
                exchange='SHFE',
                direction=signal.direction,
                offset='OPEN',
                price=open_price,
                volume=1
            )
            # Build context
            account_info = {
                'equity': self.capital,
                'available': self.capital * 0.8,
                'daily_pnl': 0,
                'margin': 10000,
            }
            context = RiskContext(
                account=account_info,
                positions={symbol: self.positions.get(symbol, {})} if symbol in self.positions else {},
                market_data={
                    'macro_score': signal.score,
                    f'{symbol}_close': close_price,
                    f'{symbol}_volume': bars[0].volume,
                    'vix_proxy': 20 + (100 - signal.score) * 0.3,
                    'timestamp': bars[-1].datetime,
                },
                order_history=[t for t in self.trades[-20:]],  # recent 20
            )
            results = self.risk_engine.check_order(order, context)
            blocked = any(r.action == RiskAction.BLOCK for r in results)
            if blocked:
                # 风控拦截
                trade = CompletedTrade(
                    symbol=symbol, open_dt=datetime.now(), close_dt=datetime.now(),
                    direction=signal.direction,
                    open_price=0, close_price=0, volume=0, size=size,
                    pnl=0, pnl_pct=0, risk_blocked=True
                )
                self.trades.append(trade)
                return

        # 5. 开仓
        entry_price = bars[0].open_price
        self.positions[symbol] = {
            'open_dt': bars[0].datetime,
            'direction': signal.direction,
            'price': entry_price,
            'volume': 1,
            'signal_score': signal.score,
        }

        # 6. 记录当日权益
        self.equity_curve.append(DailyEquity(
            date=date_str,
            equity=self.capital,
            pnl=0,  # 当日未平仓不计 pnl
            position=1 if signal.direction != 'NEUTRAL' else 0
        ))

    def _generate_report(self, symbol: str, trading_dates: List[str]) -> BacktestReport:
        """生成统计报告"""

        # 完成交易
        completed = [t for t in self.trades if t.pnl != 0 or t.risk_blocked]
        profits = [t.pnl for t in completed if t.pnl > 0]
        losses = [t.pnl for t in completed if t.pnl < 0]
        blocked_trades = [t for t in completed if t.risk_blocked]

        n = len([t for t in completed if not t.risk_blocked])
        w = len(profits)
        l = len(losses)
        wr = w / n if n > 0 else 0

        tp = sum(profits) if profits else 0
        tl = abs(sum(losses)) if losses else 0
        np_ = tp - tl
        pf = tp / tl if tl > 0 else (float('inf') if tp > 0 else 0)
        ap = tp / w if w > 0 else 0
        al = tl / l if l > 0 else 0
        mp = max(profits) if profits else 0
        ml = min(losses) if losses else 0

        # Sharpe ratio
        if n > 1:
            returns_full = [t.pnl / self.initial_capital for t in completed if not t.risk_blocked]
            avg_r = sum(returns_full) / len(returns_full)
            var = sum((r - avg_r) ** 2 for r in returns_full) / (len(returns_full) - 1)
            std = math.sqrt(var) if var > 0 else 0
            sharpe = (avg_r / std * math.sqrt(252)) if std > 0 else 0
        else:
            sharpe = 0

        # Max drawdown
        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        for t in completed:
            if not t.risk_blocked:
                equity += t.pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        final_capital = self.initial_capital + np_
        return_pct = (np_ / self.initial_capital) * 100
        days_count = len(trading_dates)
        annualized = (final_capital / self.initial_capital) ** (252 / max(days_count, 1)) - 1

        dd_pct = max_dd / peak * 100 if peak > 0 else 0
        calmar = annualized / (dd_pct / 100) if dd_pct > 0 else 0

        # Signal accuracy
        corrects = sum(1 for t in completed
                       if not t.risk_blocked
                       and ((t.direction == 'LONG' and t.pnl > 0)
                            or (t.direction == 'SHORT' and t.pnl > 0)))
        signal_acc = corrects / n * 100 if n > 0 else 0

        start = trading_dates[0]
        end = trading_dates[-1]

        return BacktestReport(
            symbol=symbol,
            start_date=start,
            end_date=end,
            total_days=days_count,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            return_pct=return_pct,
            annualized_return=annualized * 100,
            total_trades=n,
            winning_trades=w,
            losing_trades=l,
            win_rate=wr * 100,
            total_profit=tp,
            total_loss=tl,
            net_profit=np_,
            avg_profit=ap,
            avg_loss=al,
            profit_factor=pf,
            max_profit=mp,
            max_loss=ml,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_pct=dd_pct,
            calmar_ratio=calmar,
            signal_accuracy=signal_acc,
            trades=self.trades,
            equity_curve=self.equity_curve,
        )

    def _empty_report(self, symbol: str) -> BacktestReport:
        return BacktestReport(
            symbol=symbol, start_date='', end_date='', total_days=0,
            initial_capital=self.initial_capital, final_capital=self.initial_capital,
            return_pct=0, annualized_return=0, total_trades=0,
            winning_trades=0, losing_trades=0, win_rate=0,
            total_profit=0, total_loss=0, net_profit=0,
            avg_profit=0, avg_loss=0, profit_factor=0,
            max_profit=0, max_loss=0, sharpe_ratio=0,
            max_drawdown=0, max_drawdown_pct=0, calmar_ratio=0,
            signal_accuracy=0,
        )


# ============================================================
# Report Formatting
# ============================================================

def print_report(report: BacktestReport):
    """打印格式化回测报告"""
    print(f"\n{'='*70}")
    print(f"  BACKTEST REPORT: {report.symbol}")
    print(f"  {report.start_date} >> {report.end_date}  ({report.total_days} days)")
    print(f"{'='*70}")

    print(f"\n  -- Trade Statistics --")
    print(f"  Total Trades:    {report.total_trades:>8}")
    print(f"  Winning:         {report.winning_trades:>8}  ({report.win_rate:.1f}%)")
    print(f"  Losing:          {report.losing_trades:>8}")
    print(f"  Risk Blocked:    {report.total_days - report.total_trades:>8}")

    print(f"\n  -- P&L --")
    print(f"  Total Profit:    {report.total_profit:>12,.2f}")
    print(f"  Total Loss:      {report.total_loss:>12,.2f}")
    print(f"  Net Profit:      {report.net_profit:>12,.2f}")
    print(f"  Avg Profit:      {report.avg_profit:>12,.2f}")
    print(f"  Avg Loss:        {report.avg_loss:>12,.2f}")
    print(f"  Max Profit:      {report.max_profit:>12,.2f}")
    print(f"  Max Loss:        {report.max_loss:>12,.2f}")
    print(f"  Profit Factor:   {report.profit_factor:>12.2f}")

    print(f"\n  -- Risk Metrics --")
    sharpe_tag = "GOOD" if report.sharpe_ratio >= 1.0 else ("WARN" if report.sharpe_ratio >= 0 else "BAD")
    print(f"  Sharpe Ratio:    {report.sharpe_ratio:>12.3f}  [{sharpe_tag}]")
    print(f"  Max Drawdown:    {report.max_drawdown:>12,.2f}")
    print(f"  Max DD %:        {report.max_drawdown_pct:>11.2f}%")
    print(f"  Calmar Ratio:    {report.calmar_ratio:>12.2f}")

    print(f"\n  -- Returns --")
    print(f"  Initial Capital: {report.initial_capital:>12,.2f}")
    print(f"  Final Capital:   {report.final_capital:>12,.2f}")
    print(f"  Total Return:    {report.return_pct:>11.2f}%")
    print(f"  Annualized:      {report.annualized_return:>11.2f}%")

    print(f"\n  -- Signal Quality --")
    print(f"  Signal Accuracy: {report.signal_accuracy:>8.1f}%")

    # 最近 10 笔交易
    print(f"\n  -- Recent Trades (last 10) --")
    recent = [t for t in report.trades if not t.risk_blocked][-10:]
    for i, t in enumerate(recent):
        pnl_tag = '+' if t.pnl > 0 else ' '
        print(f"  {i+1:>2}. {t.open_dt.strftime('%m-%d')} {t.direction:>5} "
              f"@{t.open_price:>8.0f}> {t.close_price:>8.0f}  "
              f"pnl={pnl_tag}{t.pnl:>10,.0f}")

    print(f"{'='*70}\n")


def save_reports(reports: List[BacktestReport], filepath: str):
    """保存报告到 JSON"""
    out = {
        'generated_at': datetime.now().isoformat(),
        'initial_capital': reports[0].initial_capital if reports else 0,
        'risk_profile': 'moderate',
        'summary': {
            'total_net_profit': sum(r.net_profit for r in reports),
            'avg_sharpe': sum(r.sharpe_ratio for r in reports) / len(reports) if reports else 0,
            'avg_win_rate': sum(r.win_rate for r in reports) / len(reports) if reports else 0,
            'avg_return_pct': sum(r.return_pct for r in reports) / len(reports) if reports else 0,
        },
        'results': []
    }
    for r in reports:
        out['results'].append({
            'symbol': r.symbol,
            'period': f"{r.start_date}-{r.end_date}",
            'trades': r.total_trades,
            'win_rate': round(r.win_rate, 1),
            'net_profit': round(r.net_profit, 2),
            'profit_factor': round(r.profit_factor, 2),
            'sharpe': round(r.sharpe_ratio, 3),
            'max_dd_pct': round(r.max_drawdown_pct, 2),
            'return_pct': round(r.return_pct, 2),
            'signal_accuracy': round(r.signal_accuracy, 1),
            'annualized_return': round(r.annualized_return, 1),
        })

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Report saved: {filepath}")


# ============================================================
# Main
# ============================================================

def main():
    """主入口"""
    print("=" * 70)
    print("  SIGNAL-DRIVEN BACKTEST SYSTEM v1.0")
    print("  MacroRiskStrategy + RiskEngine + CSV Signals")
    print("=" * 70)

    # 参数
    CAPITAL = 1_000_000
    SYMBOLS = ['RU', 'ZN', 'RB', 'NI']
    RISK_PROFILES = ['conservative', 'moderate', 'aggressive']

    all_reports = []

    # 按品种 + 风险画像组合回测
    for sym in SYMBOLS:
        print(f"\n{'#'*70}")
        print(f"# {sym}")
        print(f"{'#'*70}")

        for profile in RISK_PROFILES:
            print(f"\n--- Profile: {profile} ---")
            tester = SignalDrivenBacktester(capital=CAPITAL, risk_profile=profile)
            report = tester.run(sym, days=0)  # 0 = all available data
            report.symbol = f"{sym}_{profile}"
            print_report(report)
            all_reports.append(report)

    # 跨品种对比
    print("\n" + "=" * 70)
    print("  CROSS-SYMBOL COMPARISON (moderate profile)")
    print("=" * 70)
    print(f"  {'Symbol':<12} {'Trades':>7} {'Win%':>7} {'Net PnL':>12} "
          f"{'PF':>6} {'Sharpe':>7} {'DD%':>7} {'SigAcc%':>8}")

    moderate_reports = [r for r in all_reports if r.symbol.startswith(tuple(SYMBOLS))
                        and '_moderate' in r.symbol]
    for r in moderate_reports:
        sym = r.symbol.replace('_moderate', '')
        print(f"  {sym:<12} {r.total_trades:>7} {r.win_rate:>6.1f}% "
              f"{r.net_profit:>12,.0f} {r.profit_factor:>6.2f} "
              f"{r.sharpe_ratio:>7.3f} {r.max_drawdown_pct:>6.2f}% "
              f"{r.signal_accuracy:>7.1f}%")

    # 保存
    out_path = r'D:\futures_v6\signal_backtest_report.json'
    save_reports(all_reports, out_path)

    print("\n" + "=" * 70)
    print("  BACKTEST COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
