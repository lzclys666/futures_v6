# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE, PROJECT_ROOT
"""
SignalBridge Integration Test
Verify macro signal flow from CSV -> SignalBridge -> RiskEngine
"""

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from services.signal_bridge import SignalBridge, EVENT_MACRO_SIGNAL
from services.macro_risk_app import RiskEngine, get_symbol_config
from vnpy.event import EventEngine, Event
from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.constant import Direction, Offset, Status
from unittest.mock import MagicMock
import time
import os


def create_mock_order(symbol: str, direction: Direction, price: float, volume: int) -> OrderData:
    """Create mock order for testing"""
    order = MagicMock(spec=OrderData)
    order.symbol = symbol
    order.direction = direction
    order.price = price
    order.volume = volume
    order.status = Status.SUBMITTING
    order.vt_orderid = f"{symbol}_{direction.value}_{int(time.time())}"
    order.offset = Offset.OPEN
    return order


def test_signal_bridge_integration():
    """Test complete signal flow"""
    print("=" * 60)
    print("SignalBridge Integration Test")
    print("=" * 60)
    
    # 1. Create EventEngine
    event_engine = EventEngine()
    event_engine.start()
    
    # 2. Create Mock MainEngine with SignalBridge
    main_engine = MagicMock()
    
    # 3. Create SignalBridge
    csv_dir = "str(MACRO_ENGINE)/output"
    signal_bridge = SignalBridge(csv_dir=csv_dir, event_engine=event_engine)
    
    # Manually set signals for testing
    signal_bridge._cache = {
        "AU": {"direction": "LONG", "score": 0.55, "timestamp": time.time()},  # Changed to 0.55 to trigger circuit
        "CU": {"direction": "SHORT", "score": -0.55, "timestamp": time.time()},
        "RU": {"direction": "NEUTRAL", "score": -0.05, "timestamp": time.time()},
    }
    
    # Attach to main_engine
    main_engine.signal_bridge = signal_bridge
    
    # 4. Create RiskEngine
    risk_engine = RiskEngine(main_engine, event_engine)
    
    # 5. Test macro circuit breaker
    print("\n--- Test 1: Macro Circuit Breaker ---")
    
    # Test AU (LONG signal, score 0.45) - should block SHORT
    order_short_au = create_mock_order("AU2605", Direction.SHORT, 550.0, 1)
    violations = risk_engine._check_rules(order_short_au)
    circuit_violations = [v for v in violations if v["rule"] == "宏观熔断"]
    
    if circuit_violations:
        print(f"PASS AU SHORT blocked: {circuit_violations[0]['reason']}")
    else:
        print("FAIL AU SHORT should be blocked (score 0.45 >= 0.5 threshold)")
    
    # Test CU (SHORT signal, score -0.55) - should block LONG
    order_long_cu = create_mock_order("CU2605", Direction.LONG, 70000.0, 1)
    violations = risk_engine._check_rules(order_long_cu)
    circuit_violations = [v for v in violations if v["rule"] == "宏观熔断"]
    
    if circuit_violations:
        print(f"PASS CU LONG blocked: {circuit_violations[0]['reason']}")
    else:
        print("FAIL CU LONG should be blocked (score -0.55 <= -0.5 threshold)")
    
    # 6. Test direction consistency
    print("\n--- Test 2: Direction Consistency ---")
    
    # Test AU (LONG signal) - should block SHORT
    order_short_au2 = create_mock_order("AU2606", Direction.SHORT, 551.0, 1)
    violations = risk_engine._check_rules(order_short_au2)
    direction_violations = [v for v in violations if v["rule"] == "方向一致性检查"]
    
    if direction_violations:
        print(f"PASS AU SHORT blocked by direction: {direction_violations[0]['reason']}")
    else:
        print("FAIL AU SHORT should be blocked by direction check")
    
    # Test CU (SHORT signal) - should block LONG
    order_long_cu2 = create_mock_order("CU2606", Direction.LONG, 70100.0, 1)
    violations = risk_engine._check_rules(order_long_cu2)
    direction_violations = [v for v in violations if v["rule"] == "方向一致性检查"]
    
    if direction_violations:
        print(f"PASS CU LONG blocked by direction: {direction_violations[0]['reason']}")
    else:
        print("FAIL CU LONG should be blocked by direction check")
    
    # Test RU (NEUTRAL signal) - should allow both directions
    order_long_ru = create_mock_order("RU2605", Direction.LONG, 15000.0, 1)
    violations = risk_engine._check_rules(order_long_ru)
    direction_violations = [v for v in violations if v["rule"] == "方向一致性检查"]
    
    if not direction_violations:
        print("PASS RU LONG allowed (NEUTRAL signal)")
    else:
        print("FAIL RU LONG should be allowed with NEUTRAL signal")
    
    # 7. Test position limit with capital ratio
    print("\n--- Test 3: Position Limit (Capital Ratio) ---")
    
    # Mock account with 1M balance
    account = MagicMock()
    account.balance = 1000000
    account.available = 500000
    main_engine.get_all_accounts.return_value = [account]
    
    # Mock no existing positions
    main_engine.get_all_positions.return_value = []
    
    # Test AU at 550 - should allow up to 5 lots (30% of 1M)
    order_au_5lots = create_mock_order("AU2605", Direction.LONG, 550.0, 5)
    violations = risk_engine._check_rules(order_au_5lots)
    position_violations = [v for v in violations if v["rule"] == "单品种最大持仓"]
    
    if not position_violations:
        print("PASS AU 5 lots allowed (within 30% capital limit)")
    else:
        print(f"FAIL AU 5 lots should be allowed: {position_violations[0]['reason']}")
    
    # Test AU at 550 - 10 lots should exceed limit
    order_au_10lots = create_mock_order("AU2605", Direction.LONG, 550.0, 10)
    violations = risk_engine._check_rules(order_au_10lots)
    position_violations = [v for v in violations if v["rule"] == "单品种最大持仓"]
    
    if position_violations:
        print(f"PASS AU 10 lots blocked: {position_violations[0]['reason']}")
    else:
        print("FAIL AU 10 lots should exceed 30% capital limit")
    
    # 8. Test trading hours
    print("\n--- Test 4: Trading Hours ---")
    
    from datetime import datetime
    import pytz
    
    # Mock current time as 22:00 (night session)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    night_time = datetime(2026, 4, 25, 22, 0, 0, tzinfo=beijing_tz)
    
    # We can't easily mock datetime.now(), so we'll test the function directly
    from services.macro_risk_app import is_in_trading_hours, get_trading_hours
    
    trading_hours = get_trading_hours("AU")
    
    # Test 22:00 - should be in trading hours
    from datetime import time as dt_time
    is_trading = is_in_trading_hours(trading_hours, dt_time(22, 0))
    if is_trading:
        print("PASS AU 22:00 is trading time")
    else:
        print("FAIL AU 22:00 should be trading time")
    
    # Test 03:00 - should NOT be in trading hours
    is_trading = is_in_trading_hours(trading_hours, dt_time(3, 0))
    if not is_trading:
        print("PASS AU 03:00 is non-trading time")
    else:
        print("FAIL AU 03:00 should be non-trading time")
    
    # Cleanup
    event_engine.stop()
    
    print("\n" + "=" * 60)
    print("Integration Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_signal_bridge_integration()
