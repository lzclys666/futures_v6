# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""
V6.0 Headless CTP Trader - connects Simnow and runs MacroDemoStrategy
Usage: python scripts/headless_trader.py [--symbol AU] [--no-macro]
"""

import os
import sys
import json
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime

# Environment
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
project_dir = Path(__file__).resolve().parent.parent
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))
sys.path.insert(0, str(project_dir / "strategies"))
sys.path.insert(0, str(project_dir / "services"))
vntrader_path = Path.home() / ".vntrader"
os.environ["VNTRADER_DIR"] = str(vntrader_path)

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Imports
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import OrderData, TradeData, TickData, SubscribeRequest
from vnpy.trader.constant import Status, Exchange
from vnpy.trader.event import EVENT_ORDER, EVENT_TRADE, EVENT_TICK, EVENT_LOG, EVENT_CONTRACT
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp


# Event callbacks
def on_log(event):
    log = event.data
    msg = str(log.msg) if hasattr(log, 'msg') else str(log)
    print(f"[LOG] {msg}")

def on_order(event):
    order = event.data
    print(f"[ORDER] {order.vt_orderid} | {order.symbol} {order.direction.value} "
          f"{order.offset.value} {order.volume}@{order.price} | {order.status.value}")

def on_trade(event):
    trade = event.data
    print(f"\n{'='*60}")
    print(f"[TRADE] *** HIT! {trade.vt_tradeid} | {trade.symbol} {trade.direction.value} "
          f"{trade.offset.value} {trade.volume}@{trade.price}")
    print(f"{'='*60}\n")

_tick_counter = {}
def on_tick(event):
    tick = event.data
    sym = tick.symbol
    _tick_counter[sym] = _tick_counter.get(sym, 0) + 1
    if _tick_counter[sym] % 20 == 1:
        print(f"[TICK] {tick.vt_symbol} last={tick.last_price} bid={tick.bid_price_1} ask={tick.ask_price_1}")

def on_contract(event):
    contract = event.data
    if 'AU' in contract.symbol.upper() or 'AG' in contract.symbol.upper():
        print(f"[CONTRACT] {contract.vt_symbol} exchange={contract.exchange.value} "
              f"pricetick={contract.pricetick} size={contract.size}")


def main():
    parser = argparse.ArgumentParser(description="V6.0 Headless CTP Trading")
    parser.add_argument("--symbol", default="AU", help="Symbol (AU/AG)")
    parser.add_argument("--no-macro", action="store_true", help="Disable macro filter")
    parser.add_argument("--fast", type=int, default=10, help="Fast MA window")
    parser.add_argument("--slow", type=int, default=20, help="Slow MA window")
    args = parser.parse_args()
    symbol = args.symbol.upper()

    print("=" * 60)
    print(f"Futures V6.0 - Headless Mode")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Symbol: {symbol}")
    print(f"Macro filter: {'OFF' if args.no_macro else 'ON'}")
    print(f"MA: {args.fast}/{args.slow}")
    print("=" * 60)

    # 1. Init engines
    print("\n[1/5] Initializing engines...")
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    event_engine.register(EVENT_LOG, on_log)
    event_engine.register(EVENT_ORDER, on_order)
    event_engine.register(EVENT_TRADE, on_trade)
    event_engine.register(EVENT_TICK, on_tick)
    event_engine.register(EVENT_CONTRACT, on_contract)

    # 2. Add apps
    print("[2/5] Adding CTP gateway + CTA engine...")
    main_engine.add_gateway(CtpGateway)
    cta_app = main_engine.add_app(CtaStrategyApp)
    cta_engine = main_engine.get_engine("CtaStrategy")

    strategy_dir = project_dir / "strategies"
    if strategy_dir.exists():
        cta_engine.load_strategy_class_from_folder(strategy_dir, module_name="strategies")
        class_names = cta_engine.get_all_strategy_class_names()
        print(f"  Strategy classes: {class_names}")

    # 3. Connect CTP
    print("[3/5] Connecting Simnow CTP...")
    config_path = vntrader_path / "connect_ctp.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            ctp_config = json.load(f)
        # Print config (mask password)
        for k, v in ctp_config.items():
            display = '***' if '密码' in k else v
            print(f"  {k} = {display}")
    else:
        print("  ERROR: connect_ctp.json not found!")
        return

    main_engine.connect(ctp_config, "CTP")
    print("  CTP connect request sent...")

    # 4. Wait for connection + find contract
    print("[4/5] Waiting for CTP connection (max 30s)...")
    connected = False
    target_contract = None
    for i in range(30):
        time.sleep(1)
        try:
            contracts = main_engine.get_all_contracts()
            au_contracts = [c for c in contracts if c.symbol.upper().startswith(symbol)]
            if au_contracts:
                connected = True
                print(f"  [OK] CTP connected! Found {len(au_contracts)} {symbol} contracts")
                break
        except:
            pass
        if i % 5 == 4:
            print(f"  Waiting... ({i+1}s)")

    if not connected:
        print("  [WARN] CTP connection timeout, continuing anyway...")

    # Wait for contract sync
    print("  Waiting for contract sync...")
    time.sleep(5)

    # Find target contract (nearest month futures, exclude options)
    contracts = main_engine.get_all_contracts()
    au_contracts = [
        c for c in contracts
        if c.symbol.upper().startswith(symbol)
        and c.product.value == "期货"  # Exclude options
        and not c.symbol[-1].isalpha()  # Exclude option contracts (e.g., AU2605C5200)
    ]

    if au_contracts:
        # Sort by symbol, prefer nearest month (lowest numeric suffix)
        au_contracts.sort(key=lambda c: c.symbol)
        target_contract = au_contracts[0]
        vt_symbol = target_contract.vt_symbol
        print(f"  Target: {vt_symbol} (pricetick={target_contract.pricetick}, size={target_contract.size})")
    else:
        # Fallback: use known futures contract
        vt_symbol = f"{symbol.lower()}2605.SHFE"
        print(f"  [WARN] No {symbol} futures contract found, using default: {vt_symbol}")

    # Subscribe market data
    exchange_str = vt_symbol.split('.')[-1] if '.' in vt_symbol else 'SHFE'
    try:
        exchange = Exchange[exchange_str]
    except KeyError:
        exchange = Exchange.SHFE
    sub_symbol = vt_symbol.split('.')[0]
    sub_req = SubscribeRequest(symbol=sub_symbol, exchange=exchange)
    main_engine.subscribe(sub_req, "CTP")
    print(f"  Subscribed: {vt_symbol}")

    # 5. Add and start strategy
    print("[5/5] Adding and starting strategy...")
    strategy_name = f"macro_{symbol.lower()}_demo"
    setting = {
        "fast_window": args.fast,
        "slow_window": args.slow,
        "use_macro": not args.no_macro,
        "csv_path_str": str(MACRO_ENGINE / "output" / "{symbol}_macro_daily_{date}.csv"),
    }

    try:
        cta_engine.add_strategy(
            class_name="MacroDemoStrategy",
            strategy_name=strategy_name,
            vt_symbol=vt_symbol,
            setting=setting,
        )
        print(f"  Strategy added: {strategy_name} -> {vt_symbol}")

        cta_engine.init_strategy(strategy_name)
        print(f"  Strategy initializing...")
        time.sleep(5)

        cta_engine.start_strategy(strategy_name)
        print(f"  [OK] Strategy started!")

    except Exception as e:
        print(f"  [FAIL] Strategy start failed: {e}")
        import traceback
        traceback.print_exc()

    # Main loop
    print("\n" + "=" * 60)
    print(f"System running - {datetime.now().strftime('%H:%M:%S')}")
    print(f"Symbol: {symbol} | Contract: {vt_symbol}")
    print("Press Ctrl+C to exit")
    print("=" * 60 + "\n")

    running = True
    def signal_handler(sig, frame):
        nonlocal running
        print("\n[EXIT] Shutdown signal received...")
        running = False
    signal.signal(signal.SIGINT, signal_handler)

    last_status = time.time()
    while running:
        time.sleep(1)
        if time.time() - last_status > 60:
            try:
                positions = main_engine.get_all_positions()
                orders = main_engine.get_all_orders()
                trades = main_engine.get_all_trades()
                active = [o for o in orders if o.status == Status.NOTTRADED]
                print(f"\n[STATUS] {datetime.now().strftime('%H:%M:%S')} | "
                      f"Positions: {len(positions)} | Active orders: {len(active)} | "
                      f"Total trades: {len(trades)}")
                for p in positions:
                    print(f"  Pos: {p.vt_symbol} {p.direction.value} {p.volume}@{p.price} PnL={p.pnl:.2f}")
                for t in trades[-3:]:
                    print(f"  Trade: {t.vt_symbol} {t.direction.value} {t.offset.value} {t.volume}@{t.price}")
            except Exception as e:
                print(f"[STATUS] Error: {e}")
            last_status = time.time()

    # Shutdown
    print("\n[SHUTDOWN] Closing...")
    try:
        cta_engine.stop_strategy(strategy_name)
        print("  Strategy stopped")
    except:
        pass
    try:
        main_engine.close()
        print("  Engine closed")
    except:
        pass
    print("[SHUTDOWN] Done.")


if __name__ == "__main__":
    main()
