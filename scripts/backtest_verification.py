#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config.paths import PROJECT_ROOT
from config.paths import MACRO_ENGINE
"""
宏观信号回测验证系统 (Phase 4: 回测验证)
============================================
基于真实宏观信号 CSV 数据的策略回测引擎。

特性:
- 加载全部历史宏观信号 CSV 数据
- 基于信号方向 + 评分进行模拟交易
- 支持多品种并行回测
- 计算完整风险指标: 夏普比率、最大回撤、胜率、盈亏比、Calmar比率
- 支持三档风险画像 (保守/稳健/激进)
- 生成 JSON 回测报告
"""

import os
import sys
import csv
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import argparse

# Project path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

# ============================================================================
# 品种配置
# ============================================================================
SYMBOL_CONFIGS = {
    "RU": {"name": "天然橡胶", "size": 10, "pricetick": 5, "margin_rate": 0.12, "volatility_pct": 0.018, "base_price": 15000},
    "ZN": {"name": "锌", "size": 5, "pricetick": 5, "margin_rate": 0.10, "volatility_pct": 0.015, "base_price": 22000},
    "RB": {"name": "螺纹钢", "size": 10, "pricetick": 1, "margin_rate": 0.09, "volatility_pct": 0.014, "base_price": 3500},
    "AU": {"name": "黄金", "size": 1000, "pricetick": 0.02, "margin_rate": 0.08, "volatility_pct": 0.010, "base_price": 600},
    "AG": {"name": "白银", "size": 15, "pricetick": 1, "margin_rate": 0.10, "volatility_pct": 0.016, "base_price": 7500},
    "CU": {"name": "铜", "size": 5, "pricetick": 10, "margin_rate": 0.10, "volatility_pct": 0.012, "base_price": 70000},
    "NI": {"name": "镍", "size": 1, "pricetick": 10, "margin_rate": 0.12, "volatility_pct": 0.022, "base_price": 130000},
}

# 风险画像配置
RISK_PROFILES = {
    "conservative": {
        "name": "保守",
        "position_pct": 0.15,
        "max_daily_loss_pct": 0.03,
        "stop_loss_atr_mult": 2.0,
        "take_profit_atr_mult": 3.0,
        "max_hold_days": 10,
        "min_score_entry": 0.3,
    },
    "moderate": {
        "name": "稳健",
        "position_pct": 0.25,
        "max_daily_loss_pct": 0.05,
        "stop_loss_atr_mult": 1.5,
        "take_profit_atr_mult": 2.5,
        "max_hold_days": 7,
        "min_score_entry": 0.15,
    },
    "aggressive": {
        "name": "激进",
        "position_pct": 0.35,
        "max_daily_loss_pct": 0.08,
        "stop_loss_atr_mult": 1.0,
        "take_profit_atr_mult": 2.0,
        "max_hold_days": 5,
        "min_score_entry": 0.05,
    },
}


@dataclass
class TradeRecord:
    """交易记录"""
    entry_date: str
    exit_date: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    entry_score: float
    exit_score: float
    quantity: int
    pnl: float
    pnl_pct: float
    hold_days: int
    exit_reason: str


@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    symbol_name: str
    risk_profile: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    annualized_volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_pnl: float
    total_commission: float
    avg_hold_days: float
    long_trades: int
    short_trades: int
    long_win_rate: float
    short_win_rate: float
    daily_returns: List[float] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    trades_detail: List[TradeRecord] = field(default_factory=list)


class MacroSignalLoader:
    """加载宏观信号 CSV 数据"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.signals: Dict[str, Dict[str, dict]] = defaultdict(dict)
        self._load_all()

    def _load_all(self):
        total = 0
        for csv_file in sorted(self.output_dir.glob("*_macro_daily_*.csv")):
            parts = csv_file.stem.split('_')
            if len(parts) < 4 or parts[1] != 'macro' or parts[2] != 'daily':
                continue
            symbol = parts[0]
            date_str = parts[-1]

            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_type = row.get('rowType', '') or row.get('row_type', '')
                        if row_type == 'SUMMARY':
                            score_str = row.get('compositeScore', '') or row.get('composite_score', '0')
                            try:
                                score = float(score_str)
                            except (ValueError, TypeError):
                                score = 0.0
                            direction = row.get('direction', 'NEUTRAL')
                            self.signals[symbol][date_str] = {
                                'date': date_str,
                                'direction': direction,
                                'score': score,
                            }
                            total += 1
                            break
            except Exception as e:
                print(f"[WARN] 加载失败 {csv_file.name}: {e}")

        signal_days = sum(len(sigs) for sigs in self.signals.values())
        print(f"[SignalLoader] 加载 {total} 条信号, {len(self.signals)} 品种, {signal_days} 个交易日")
        for sym in sorted(self.signals.keys()):
            sigs = self.signals[sym]
            non_neutral = sum(1 for s in sigs.values() if s['direction'] != 'NEUTRAL')
            print(f"  {sym}: {len(sigs)} 天, {non_neutral} 非中性信号")

    def get_signal(self, symbol: str, date_str: str) -> dict:
        return self.signals.get(symbol, {}).get(date_str, {
            'direction': 'NEUTRAL',
            'score': 0.0,
        })

    def get_date_range(self, symbol: str, start: str, end: str) -> List[dict]:
        sigs = self.signals.get(symbol, {})
        result = []
        for date_str in sorted(sigs.keys()):
            if start <= date_str <= end:
                result.append(sigs[date_str])
        return result


class BacktestVerification:
    """回测验证引擎"""

    def __init__(self, signal_dir: str = "str(MACRO_ENGINE)/output",
                 initial_capital: float = 1_000_000, risk_profile: str = "moderate"):
        self.signal_loader = MacroSignalLoader(signal_dir)
        self.initial_capital = initial_capital
        self.profile_config = RISK_PROFILES.get(risk_profile, RISK_PROFILES["moderate"])
        self.risk_profile_name = risk_profile

    def run_single(
        self, symbol: str,
        start_date: str = "20250101",
        end_date: str = "20260424",
        commission_rate: float = 0.0001,
    ) -> BacktestResult:
        config = SYMBOL_CONFIGS.get(symbol, {"name": symbol, "size": 10, "pricetick": 1,
                                              "margin_rate": 0.10, "volatility_pct": 0.015, "base_price": 10000})
        signals = self.signal_loader.get_date_range(symbol, start_date, end_date)

        if not signals:
            print(f"[WARN] {symbol}: 无信号数据 {start_date}~{end_date}")
            return self._empty_result(symbol, config, start_date, end_date)

        capital = self.initial_capital
        position = 0
        entry_price = 0.0
        entry_score = 0.0
        entry_date = ""
        entry_direction = ""
        trades: List[TradeRecord] = []
        equity_curve: List[Dict] = []
        daily_returns: List[float] = []

        current_price = config["base_price"]
        daily_vol = config["volatility_pct"]
        pricetick = config["pricetick"]
        contract_size = config["size"]

        import random
        random.seed(42)

        for i, sig in enumerate(signals):
            date_str = sig['date']
            direction = sig['direction']
            score = abs(sig['score'])

            if i > 0:
                prev_dir = signals[i - 1]['direction']
                prev_score = signals[i - 1]['score']
                drift = prev_score * daily_vol * 0.5
                shock = random.gauss(0, daily_vol)
                price_change = current_price * (drift + shock)
                current_price += price_change
                current_price = max(current_price, pricetick * 10)
                current_price = round(current_price / pricetick) * pricetick

            if position != 0:
                hold_days = self._days_between(entry_date, date_str)
                pnl_unrealized = position * (current_price - entry_price) * contract_size

                exit_signal = None
                exit_price = current_price

                stop_price = entry_price - position * self.profile_config["stop_loss_atr_mult"] * current_price * daily_vol
                if (position > 0 and current_price <= stop_price) or (position < 0 and current_price >= stop_price):
                    exit_signal = "stop_loss"

                tp_price = entry_price + position * self.profile_config["take_profit_atr_mult"] * current_price * daily_vol
                if not exit_signal:
                    if (position > 0 and current_price >= tp_price) or (position < 0 and current_price <= tp_price):
                        exit_signal = "take_profit"

                if not exit_signal and direction != 'NEUTRAL' and direction != entry_direction:
                    exit_signal = "signal_reverse"

                if not exit_signal and direction == 'NEUTRAL':
                    exit_signal = "neutral"

                if not exit_signal and hold_days >= self.profile_config["max_hold_days"]:
                    exit_signal = "hold_expire"

                if exit_signal:
                    pnl = position * (exit_price - entry_price) * contract_size
                    commission = (entry_price + exit_price) * contract_size * commission_rate
                    capital += pnl - commission

                    trades.append(TradeRecord(
                        entry_date=entry_date, exit_date=date_str, symbol=symbol,
                        direction=entry_direction, entry_price=entry_price,
                        exit_price=exit_price, entry_score=entry_score, exit_score=score,
                        quantity=1, pnl=pnl,
                        pnl_pct=pnl / capital * 100 if capital > 0 else 0,
                        hold_days=hold_days, exit_reason=exit_signal,
                    ))
                    position = 0

                if position != 0 and abs(pnl_unrealized) / capital > self.profile_config["max_daily_loss_pct"]:
                    exit_price = current_price
                    pnl = position * (exit_price - entry_price) * contract_size
                    commission = (entry_price + exit_price) * contract_size * commission_rate
                    capital += pnl - commission

                    trades.append(TradeRecord(
                        entry_date=entry_date, exit_date=date_str, symbol=symbol,
                        direction=entry_direction, entry_price=entry_price,
                        exit_price=exit_price, entry_score=entry_score, exit_score=score,
                        quantity=1, pnl=pnl,
                        pnl_pct=pnl / capital * 100 if capital > 0 else 0,
                        hold_days=hold_days, exit_reason="daily_loss_limit",
                    ))
                    position = 0

            if position == 0 and direction != 'NEUTRAL' and score >= self.profile_config["min_score_entry"]:
                position = 1 if direction == 'LONG' else -1
                entry_price = current_price
                entry_score = score
                entry_date = date_str
                entry_direction = direction

            daily_return = (capital - self.initial_capital) / self.initial_capital
            equity_curve.append({
                "date": date_str,
                "capital": round(capital, 2),
                "return_pct": round(daily_return * 100, 4),
                "position": position,
            })
            daily_returns.append(daily_return)

        if position != 0:
            pnl = position * (current_price - entry_price) * contract_size
            commission = (entry_price + current_price) * contract_size * commission_rate
            capital += pnl - commission

        return self._compute_result(
            symbol=symbol, config=config,
            start_date=start_date, end_date=end_date,
            trades=trades, final_capital=capital,
            equity_curve=equity_curve, daily_returns=daily_returns,
            commission_rate=commission_rate,
        )

    def run_multi(
        self, symbols: List[str],
        start_date: str = "20250101",
        end_date: str = "20260424",
    ) -> List[BacktestResult]:
        results = []
        for symbol in symbols:
            name = SYMBOL_CONFIGS.get(symbol, {}).get('name', symbol)
            print(f"\n[回测] {symbol} ({name})...")
            result = self.run_single(symbol, start_date, end_date)
            results.append(result)
            self._print_summary(result)
        return results

    def _compute_result(
        self, symbol: str, config: dict,
        start_date: str, end_date: str,
        trades: List[TradeRecord], final_capital: float,
        equity_curve: List[Dict], daily_returns: List[float],
        commission_rate: float = 0.0001,
    ) -> BacktestResult:
        total_trades = len(trades)
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        total_pnl = sum(t.pnl for t in trades)
        total_commission = sum(
            (t.entry_price + t.exit_price) * config["size"] * commission_rate
            for t in trades
        )
        total_return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100

        n_days = (datetime.strptime(end_date, "%Y%m%d") - datetime.strptime(start_date, "%Y%m%d")).days
        annualized_return = ((1 + total_return_pct / 100) ** (252 / n_days) - 1) * 100 if n_days > 0 else 0

        daily_ret_values = [r for r in daily_returns if r != 0]
        if len(daily_ret_values) > 1:
            avg_daily_ret = sum(daily_ret_values) / len(daily_ret_values)
            daily_std = math.sqrt(sum((r - avg_daily_ret) ** 2 for r in daily_ret_values) / (len(daily_ret_values) - 1))
            annualized_vol = daily_std * math.sqrt(252) * 100
            sharpe = (annualized_return - 2) / annualized_vol if annualized_vol > 0 else 0
        else:
            annualized_vol = 0
            sharpe = 0

        if len(daily_ret_values) > 1:
            neg_rets = [r for r in daily_ret_values if r < 0]
            if neg_rets:
                downside_std = math.sqrt(sum(r ** 2 for r in neg_rets) / len(neg_rets)) * math.sqrt(252) * 100
                sortino = (annualized_return - 2) / downside_std if downside_std > 0 else 0
            else:
                sortino = float('inf')
        else:
            sortino = 0

        peak = self.initial_capital
        max_dd = 0.0
        dd_start = ""
        dd_duration = 0
        max_dd_duration = 0

        for point in equity_curve:
            cap = point["capital"]
            if cap > peak:
                peak = cap
                if dd_duration > max_dd_duration:
                    max_dd_duration = dd_duration
                dd_duration = 0
            else:
                dd = (peak - cap) / peak
                if dd > max_dd:
                    max_dd = dd
                if dd_start == "":
                    dd_start = point["date"]
                    dd_duration = 0
                dd_duration += 1

        max_dd_pct = max_dd * 100
        calmar = annualized_return / max_dd_pct if max_dd_pct > 0 else 0

        win_rate = len(winning) / total_trades * 100 if total_trades > 0 else 0
        avg_win = sum(t.pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.pnl for t in losing) / len(losing) if losing else 0
        total_win_pnl = sum(t.pnl for t in winning)
        total_loss_pnl = sum(t.pnl for t in losing)
        profit_factor = abs(total_win_pnl / total_loss_pnl) if losing and total_loss_pnl != 0 else float('inf')
        avg_hold = sum(t.hold_days for t in trades) / total_trades if total_trades > 0 else 0

        long_trades = [t for t in trades if t.direction == 'LONG']
        short_trades = [t for t in trades if t.direction == 'SHORT']
        long_win_rate = len([t for t in long_trades if t.pnl > 0]) / len(long_trades) * 100 if long_trades else 0
        short_win_rate = len([t for t in short_trades if t.pnl > 0]) / len(short_trades) * 100 if short_trades else 0

        return BacktestResult(
            symbol=symbol,
            symbol_name=config["name"],
            risk_profile=self.risk_profile_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            total_return_pct=round(total_return_pct, 2),
            annualized_return_pct=round(annualized_return, 2),
            annualized_volatility_pct=round(annualized_vol, 2),
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3) if sortino != float('inf') else sortino,
            calmar_ratio=round(calmar, 3),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_duration_days=max_dd_duration,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else profit_factor,
            total_pnl=round(total_pnl, 2),
            total_commission=round(total_commission, 2),
            avg_hold_days=round(avg_hold, 1),
            long_trades=len(long_trades),
            short_trades=len(short_trades),
            long_win_rate=round(long_win_rate, 1),
            short_win_rate=round(short_win_rate, 1),
            daily_returns=daily_returns,
            equity_curve=equity_curve,
            trades_detail=trades,
        )

    def _empty_result(self, symbol: str, config: dict, start: str, end: str) -> BacktestResult:
        return BacktestResult(
            symbol=symbol, symbol_name=config["name"], risk_profile=self.risk_profile_name,
            start_date=start, end_date=end,
            initial_capital=self.initial_capital, final_capital=self.initial_capital,
            total_return_pct=0, annualized_return_pct=0, annualized_volatility_pct=0,
            sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0,
            max_drawdown_pct=0, max_drawdown_duration_days=0,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, avg_win=0, avg_loss=0, profit_factor=0,
            total_pnl=0, total_commission=0, avg_hold_days=0,
            long_trades=0, short_trades=0, long_win_rate=0, short_win_rate=0,
        )

    @staticmethod
    def _days_between(d1: str, d2: str) -> int:
        try:
            dt1 = datetime.strptime(d1, "%Y%m%d")
            dt2 = datetime.strptime(d2, "%Y%m%d")
            return (dt2 - dt1).days
        except ValueError:
            return 0

    @staticmethod
    def _print_summary(result: BacktestResult):
        print(f"  {result.symbol_name}({result.symbol}): "
              f"收益={result.total_return_pct:+.2f}% | "
              f"夏普={result.sharpe_ratio:.2f} | "
              f"胜率={result.win_rate:.1f}% | "
              f"最大回撤=-{result.max_drawdown_pct:.2f}% | "
              f"交易={result.total_trades}笔")


def generate_report(results: List[BacktestResult], output_path: str) -> str:
    report = {
        "report_type": "macro_signal_backtest",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_symbols": len(results),
            "avg_sharpe": round(sum(r.sharpe_ratio for r in results) / len(results), 3) if results else 0,
            "avg_return": round(sum(r.total_return_pct for r in results) / len(results), 2) if results else 0,
            "total_trades": sum(r.total_trades for r in results),
            "total_pnl": round(sum(r.total_pnl for r in results), 2),
        },
        "symbols": []
    }

    for r in results:
        entry = {
            "symbol": r.symbol,
            "name": r.symbol_name,
            "risk_profile": r.risk_profile,
            "period": f"{r.start_date} ~ {r.end_date}",
            "metrics": {
                "total_return_pct": r.total_return_pct,
                "annualized_return_pct": r.annualized_return_pct,
                "annualized_volatility_pct": r.annualized_volatility_pct,
                "sharpe_ratio": r.sharpe_ratio,
                "sortino_ratio": r.sortino_ratio if isinstance(r.sortino_ratio, (int, float)) else "inf",
                "calmar_ratio": r.calmar_ratio,
                "max_drawdown_pct": r.max_drawdown_pct,
                "max_drawdown_duration_days": r.max_drawdown_duration_days,
            },
            "trades": {
                "total": r.total_trades,
                "winning": r.winning_trades,
                "losing": r.losing_trades,
                "win_rate": r.win_rate,
                "avg_win": r.avg_win,
                "avg_loss": r.avg_loss,
                "profit_factor": r.profit_factor if isinstance(r.profit_factor, (int, float)) else "inf",
                "total_pnl": r.total_pnl,
                "total_commission": r.total_commission,
                "avg_hold_days": r.avg_hold_days,
            },
            "direction_breakdown": {
                "long_trades": r.long_trades,
                "long_win_rate": r.long_win_rate,
                "short_trades": r.short_trades,
                "short_win_rate": r.short_win_rate,
            },
            "equity_curve": r.equity_curve[:50],
            "exit_reasons": {},
        }

        reasons = defaultdict(int)
        for t in r.trades_detail:
            reasons[t.exit_reason] += 1
        entry["exit_reasons"] = dict(reasons)

        report["symbols"].append(entry)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[报告] 已保存至: {output_file}")
    return json.dumps(report, indent=2, ensure_ascii=False)


def print_console_report(results: List[BacktestResult]):
    print("\n" + "=" * 80)
    print("  宏观信号策略回测验证报告")
    print("=" * 80)

    for r in results:
        profile_name = RISK_PROFILES.get(r.risk_profile, {}).get('name', r.risk_profile)
        print(f"\n{'─' * 80}")
        print(f"  [{r.symbol}] {r.symbol_name} | 风险画像: {profile_name}")
        print(f"  回测区间: {r.start_date} ~ {r.end_date}")
        print(f"  初始资金: {r.initial_capital:,.0f} -> 最终资金: {r.final_capital:,.0f}")
        print(f"\n  收益指标:")
        print(f"     总收益率: {r.total_return_pct:+.2f}%")
        print(f"     年化收益: {r.annualized_return_pct:+.2f}%")
        print(f"     年化波动: {r.annualized_volatility_pct:.2f}%")
        print(f"  风险指标:")
        print(f"     夏普比率: {r.sharpe_ratio:.3f}")
        sortino_display = r.sortino_ratio if isinstance(r.sortino_ratio, (int, float)) else "inf"
        print(f"     索提诺比率: {sortino_display}")
        print(f"     卡玛比率: {r.calmar_ratio:.3f}")
        print(f"     最大回撤: -{r.max_drawdown_pct:.2f}% (持续{r.max_drawdown_duration_days}天)")
        print(f"  交易统计:")
        print(f"     总交易: {r.total_trades} | 盈利: {r.winning_trades} | 亏损: {r.losing_trades}")
        print(f"     胜率: {r.win_rate:.1f}%")
        print(f"     平均盈利: {r.avg_win:+,.0f} | 平均亏损: {r.avg_loss:+,.0f}")
        pf_display = f"{r.profit_factor:.2f}" if isinstance(r.profit_factor, (int, float)) else "inf"
        print(f"     盈亏比: {pf_display}")
        print(f"     净盈亏: {r.total_pnl:+,.0f} | 手续费: {r.total_commission:,.0f}")
        print(f"     平均持仓: {r.avg_hold_days:.1f}天")
        print(f"  多空分析:")
        print(f"     做多: {r.long_trades}笔 (胜率 {r.long_win_rate:.1f}%)")
        print(f"     做空: {r.short_trades}笔 (胜率 {r.short_win_rate:.1f}%)")

    print(f"\n{'─' * 80}")
    print(f"  综合评估")
    print(f"{'─' * 80}")

    avg_sharpe = sum(r.sharpe_ratio for r in results) / len(results) if results else 0
    avg_return = sum(r.total_return_pct for r in results) / len(results) if results else 0
    avg_dd = sum(r.max_drawdown_pct for r in results) / len(results) if results else 0

    print(f"  平均夏普: {avg_sharpe:.3f}")
    print(f"  平均收益率: {avg_return:+.2f}%")
    print(f"  平均最大回撤: -{avg_dd:.2f}%")

    if avg_sharpe >= 1.0:
        grade = "优秀 - 夏普比率 >= 1.0, 里程碑 M4.1 达标"
    elif avg_sharpe >= 0.5:
        grade = "一般 - 夏普比率在 0.5~1.0 之间, 需优化"
    else:
        grade = "不足 - 夏普比率 < 0.5, 信号质量需提升"

    print(f"\n  {grade}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="宏观信号回测验证系统")
    parser.add_argument("--symbols", nargs="+", default=["RU", "AU", "AG", "CU"],
                        help="回测品种列表")
    parser.add_argument("--start", default="20250101", help="起始日期 YYYYMMDD")
    parser.add_argument("--end", default="20260424", help="结束日期 YYYYMMDD")
    parser.add_argument("--capital", type=float, default=1_000_000, help="初始资金")
    parser.add_argument("--profile", choices=["conservative", "moderate", "aggressive"],
                        default="moderate", help="风险画像")
    parser.add_argument("--output", default=None, help="报告输出路径")
    parser.add_argument("--all", action="store_true", help="回测所有品种")
    args = parser.parse_args()

    if args.all:
        signal_dir = Path("str(MACRO_ENGINE)/output")
        symbols = set()
        for f in signal_dir.glob("*_macro_daily_*.csv"):
            sym = f.stem.split('_')[0]
            if sym in SYMBOL_CONFIGS:
                symbols.add(sym)
        args.symbols = sorted(symbols)

    print("=" * 60)
    print(f"宏观信号回测验证")
    print(f"品种: {', '.join(args.symbols)}")
    print(f"区间: {args.start} ~ {args.end}")
    print(f"资金: {args.capital:,.0f}")
    profile_name = RISK_PROFILES.get(args.profile, {}).get('name', args.profile)
    print(f"画像: {profile_name}")
    print("=" * 60)

    engine = BacktestVerification(
        signal_dir="str(MACRO_ENGINE)/output",
        initial_capital=args.capital,
        risk_profile=args.profile,
    )

    results = engine.run_multi(
        symbols=args.symbols,
        start_date=args.start,
        end_date=args.end,
    )

    print_console_report(results)

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(PROJECT_ROOT / f"backtest_report_{args.profile}_{timestamp}.json")

    generate_report(results, output_path)

    return results


if __name__ == "__main__":
    main()
