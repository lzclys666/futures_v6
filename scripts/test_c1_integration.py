# scripts/test_c1_integration.py
"""
C1: VNpyBridge Integration Test

Tests (run during market hours):
1. API health check (/health)
2. Strategy registry (/api/strategy/*)
3. Signal data flow (/api/macro/signal/*)
4. Risk rules status (/api/macro/factor/*)
5. CTP connection status
6. Real-time market data (during trading hours only)
"""

import json
import sys
import time
from datetime import datetime

import requests

BASE = "http://localhost:8000"
PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def check(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    elif "WARN" in detail.upper():
        WARN_COUNT += 1
        print(f"  [WARN] {name} -- {detail}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} -- {detail}")


def test_health():
    print("\n[1] API Health Check")
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        check("GET /health 200", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        check("status=ok", data.get("status") == "ok", f"status={data.get('status')}")
    except Exception as e:
        check("GET /health", False, str(e))


def test_strategy_registry():
    print("\n[2] Strategy Registry")
    try:
        r = requests.get(f"{BASE}/api/strategy/list", timeout=5)
        check("GET /api/strategy/list 200", r.status_code == 200)
        data = r.json()
        count = data.get("count", 0)
        check("Discovered strategies", count > 0, f"count={count}")
        names = [s["class_name"] for s in data.get("strategies", [])]
        check("MacroRiskStrategy exists", "MacroRiskStrategy" in names, f"found={names}")
    except Exception as e:
        check("Strategy list", False, str(e))

    try:
        r = requests.get(f"{BASE}/api/strategy/validate", timeout=5)
        data = r.json()
        check("Bindings valid", data.get("valid") == True, f"errors={data.get('errors')}")
    except Exception as e:
        check("Bindings validation", False, str(e))

    try:
        r = requests.get(f"{BASE}/api/strategy/bindings", timeout=5)
        data = r.json()
        enabled = data.get("enabled", 0)
        check("Has enabled bindings", enabled > 0, f"enabled={enabled}")
    except Exception as e:
        check("Bindings", False, str(e))


def test_signal_data():
    print("\n[3] Signal Data Flow")
    try:
        r = requests.get(f"{BASE}/api/macro/signal/all", timeout=5)
        check("GET /api/macro/signal/all 200", r.status_code == 200)
        data = r.json()
        inner = data.get("data", data)
        if isinstance(inner, list):
            check("Has signals", len(inner) > 0, f"count={len(inner)}")
        elif isinstance(inner, dict):
            check("Has signals", len(inner) > 1, f"keys={list(inner.keys())[:5]}")
    except Exception as e:
        check("Signal data", False, str(e))

    for sym in ["RU", "AU"]:
        try:
            r = requests.get(f"{BASE}/api/macro/signal/{sym}", timeout=5)
            check(f"GET /api/macro/signal/{sym}", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            check(f"Signal {sym}", False, str(e))


def test_risk_rules():
    print("\n[4] Risk Rules Status")
    try:
        r = requests.get(f"{BASE}/api/macro/factor/RU", timeout=5)
        check("GET /api/macro/factor/RU 200", r.status_code == 200)
        data = r.json()
        inner = data.get("data", data)
        if isinstance(inner, list) and len(inner) > 0:
            factor = inner[0]
            risk_fields = [k for k in factor.keys() if k.startswith("r") and "_" in k]
            check("Has risk fields", len(risk_fields) >= 10, f"count={len(risk_fields)}")
            check("R8 exists", "r8_trading_hours" in factor)
            check("R12 exists", "r12_cancel_limit" in factor)
        else:
            check("Factor data format", False, f"type={type(inner)}")
    except Exception as e:
        check("Risk rules", False, str(e))


def test_ctp_connection():
    print("\n[5] CTP Connection")
    try:
        r = requests.get(f"{BASE}/api/macro/signal/all", timeout=5)
        check("API backend running", r.status_code == 200)
    except Exception as e:
        check("API backend", False, str(e))

    try:
        r = requests.get(f"{BASE}/api/vnpy/status", timeout=5)
        if r.status_code == 200:
            check("VNpy status queryable", True)
        else:
            check("VNpy status", False, f"status={r.status_code}", "WARN")
    except Exception as e:
        check("VNpy status", False, str(e), "WARN")


def test_market_data():
    print("\n[6] Real-time Market Data (trading hours only)")
    now = datetime.now()
    hour, minute = now.hour, now.minute

    in_day = (hour == 9 and minute >= 0) or (9 < hour < 15)
    in_night = hour >= 21 or hour < 3
    in_session = in_day or in_night

    if not in_session:
        print(f"  [SKIP] Not in trading hours ({now.strftime('%H:%M')}), day=9-15/night=21-02:30")
        return

    print(f"  [INFO] Trading session ({now.strftime('%H:%M')}), checking market data...")
    try:
        r = requests.get(f"{BASE}/api/macro/signal/all", timeout=10)
        data = r.json()
        inner = data.get("data", data)
        if isinstance(inner, list):
            for item in inner[:3]:
                sym = item.get("symbol", item.get("code", "?"))
                score = item.get("compositeScore", item.get("composite_score", 0))
                direction = item.get("direction", "N/A")
                print(f"  [INFO] {sym}: score={score}, direction={direction}")
        elif isinstance(inner, dict):
            for sym in ["RU", "CU", "AU", "AG"]:
                sym_data = inner.get(sym, {})
                if isinstance(sym_data, dict):
                    score = sym_data.get("compositeScore", sym_data.get("composite_score", 0))
                    direction = sym_data.get("direction", "N/A")
                    print(f"  [INFO] {sym}: score={score}, direction={direction}")
    except Exception as e:
        check("Market data", False, str(e), "WARN")


def main():
    print("=" * 60)
    print(f"C1: VNpyBridge Integration Test -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_health()
    test_strategy_registry()
    test_signal_data()
    test_risk_rules()
    test_ctp_connection()
    test_market_data()

    print("\n" + "=" * 60)
    print(f"Result: {PASS_COUNT} PASS / {FAIL_COUNT} FAIL / {WARN_COUNT} WARN")
    print("=" * 60)

    if FAIL_COUNT > 0:
        print(f"\n[WARNING] {FAIL_COUNT} FAIL items need fix")
        return 1
    elif WARN_COUNT > 0:
        print("\n[PASS] with warnings")
        return 0
    else:
        print("\n[PASS] All tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
