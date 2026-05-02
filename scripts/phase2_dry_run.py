# -*- coding: utf-8 -*-
"""
Phase 2 Dry-Run - strategy init, signal read, direction, risk check, order logic
Non-trading hours validation script.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.risk_manager import RiskManager
from vnpy.trader.constant import Direction, Offset


def test_risk_manager():
    print("=" * 60)
    print("[1/4] Risk Manager Test")
    print("=" * 60)

    rm = RiskManager(config={
        "max_position": {"enable": True, "max_lots": 10},
        "max_daily_loss": {"enable": True, "max_loss": 5000.0},
        "price_limit": {"enable": True},
    })
    cfg = rm.get_config()
    print(f"  Rule1 max_position: enable={cfg['max_position']['enable']}, max_lots={cfg['max_position']['max_lots']}")
    print(f"  Rule2 max_daily_loss: enable={cfg['max_daily_loss']['enable']}, max_loss={cfg['max_daily_loss']['max_loss']}")
    print(f"  Rule3 price_limit: enable={cfg['price_limit']['enable']}")

    # Normal order should pass
    ok, reason = rm.check_order("RU2409.SF", Direction.LONG, Offset.OPEN, 1, 14850.0)
    assert ok, f"Normal order should pass but rejected: {reason}"
    print(f"  PASS: RU LONG 1lot @ 14850 -> approved")

    # Over-position should be rejected
    rm._pos_cache["RU2409.SF"] = 10
    ok, reason = rm.check_order("RU2409.SF", Direction.LONG, Offset.OPEN, 1, 14850.0)
    assert not ok, "Over-position should be rejected"
    print(f"  PASS: RU 10lots+1 -> rejected [{reason[:40]}...]")

    # Daily loss exceeded
    rm._pos_cache["RU2409.SF"] = 0
    rm._daily_pnl_cache = -5500.0  # Already exceeded 5000 limit
    ok, reason = rm.check_order("RU2409.SF", Direction.LONG, Offset.OPEN, 1, 14850.0)
    assert not ok, "Daily loss exceeded should be rejected"
    print(f"  PASS: daily loss -5500 (limit 5000) -> rejected")

    # Close position should pass even with daily loss exceeded
    ok, reason = rm.check_order("RU2409.SF", Direction.SHORT, Offset.CLOSE, 1, 14850.0)
    assert ok, "Close position should not be blocked by daily loss limit"
    print(f"  PASS: close position with daily loss exceeded -> approved")

    # Independent switch
    rm2 = RiskManager(config={"max_position": {"enable": False}})
    ok, reason = rm2.check_order("RU2409.SF", Direction.LONG, Offset.OPEN, 100, 14850.0)
    assert ok, "Should pass with max_position disabled"
    print(f"  PASS: max_position OFF, 100lots -> approved")

    print()


def test_csv_signal_read():
    print("=" * 60)
    print("[2/4] CSV Signal Read Test")
    print("=" * 60)

    import csv
    from datetime import datetime

    output_dir = PROJECT_ROOT / "macro_engine" / "output"
    today = datetime.now().strftime("%Y%m%d")

    csv_files = list(output_dir.glob(f"*_macro_daily_{today}.csv"))
    if not csv_files:
        print(f"  WARN: No CSV for today ({today}), checking latest...")
        all_csvs = sorted(output_dir.glob("*_macro_daily_*.csv"), reverse=True)
        if all_csvs:
            csv_files = [all_csvs[0]]
            print(f"  Using: {all_csvs[0].name}")
        else:
            print("  FAIL: No CSV files found")
            return

    for csv_path in csv_files[:4]:
        symbol = csv_path.name.split("_")[0]
        direction = "NEUTRAL"
        score = 0.0
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_type = row.get("rowType", "") or row.get("row_type", "")
                    row_symbol = row.get("symbol", "") or row.get("\ufeffsymbol", "")
                    if row_type == "SUMMARY" and row_symbol == symbol:
                        direction = row["direction"]
                        score_str = row.get("compositeScore", "") or row.get("composite_score", "")
                        score = float(score_str) if score_str else 0.0
                        break
            print(f"  PASS: {symbol}: direction={direction}, score={score:.4f}")
        except Exception as e:
            print(f"  FAIL: {symbol}: {e}")

    print()


def test_strategy_import():
    print("=" * 60)
    print("[3/4] Strategy Import Test")
    print("=" * 60)

    from strategies.macro_demo_strategy import MacroDemoStrategy
    print(f"  PASS: MacroDemoStrategy imported")
    print(f"     parameters: {MacroDemoStrategy.parameters}")
    print(f"     variables: {MacroDemoStrategy.variables}")
    print()


def test_full_chain():
    print("=" * 60)
    print("[4/4] Full Chain Simulation")
    print("=" * 60)

    rm = RiskManager()
    scenarios = [
        ("RU", Direction.LONG, Offset.OPEN, 1, 14850.0, "normal long"),
        ("CU", Direction.SHORT, Offset.OPEN, 2, 78500.0, "normal short"),
        ("AG", Direction.LONG, Offset.OPEN, 15, 5800.0, "over-position"),
    ]
    for symbol, direction, offset, volume, price, desc in scenarios:
        vt_symbol = f"{symbol}2409.SF"
        ok, reason = rm.check_order(vt_symbol, direction, offset, volume, price)
        status = "PASS" if ok else "REJECT"
        print(f"  {status}: {symbol} {direction.value} {offset.value} {volume}lot @ {price} ({desc})")
        if not ok:
            print(f"         reason: {reason[:60]}")

    print()
    print("=" * 60)
    print("Phase 2 Dry-Run COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_risk_manager()
    test_csv_signal_read()
    test_strategy_import()
    test_full_chain()
