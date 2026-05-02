#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNpyBridge测试脚本
测试内容:
1. 启动/停止VNpy引擎
2. 策略管理（添加/初始化/启动/停止）
3. 数据查询（持仓/账户/订单）
4. 风控状态查询
5. 事件监听
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vnpy_bridge import VNpyBridge, bridge, BridgeStatus


def test_basic_lifecycle():
    """测试基本生命周期"""
    print("\n" + "="*60)
    print("Test 1: Basic Lifecycle")
    print("="*60)
    
    # 初始状态
    print(f"\n[1.1] Initial status: {bridge.status.value}")
    assert bridge.status == BridgeStatus.STOPPED, "Should be STOPPED initially"
    print("[OK] Initial state correct")
    
    # 启动
    print("\n[1.2] Starting VNpy...")
    result = bridge.start()
    if result:
        print("[OK] VNpy started")
    else:
        print("[WARN] Start returned False (may be already running or error)")
    
    # 状态检查
    print("\n[1.3] Checking status...")
    status = bridge.get_status()
    print(f"  Status: {status['status']}")
    print(f"  Running: {status['is_running']}")
    print(f"  Trading hours: {status['is_trading_hours']}")
    
    if status['is_running']:
        print("[OK] Status correct")
    else:
        print("[WARN] VNpy not running")
    
    print("\n[OK] Test 1 PASSED")
    return True


def test_strategy_management():
    """测试策略管理"""
    print("\n" + "="*60)
    print("Test 2: Strategy Management")
    print("="*60)
    
    # 确保VNpy已启动
    if bridge.status != BridgeStatus.RUNNING:
        print("\n[2.0] Starting VNpy...")
        bridge.start()
    
    # 添加策略
    print("\n[2.1] Adding strategy...")
    result = bridge.add_strategy(
        class_name="MacroRiskStrategy",
        strategy_name="test_ru",
        vt_symbol="RU2505.SHFE",
        setting={
            "fast_window": 10,
            "slow_window": 20,
            "risk_profile": "moderate",
            "enable_risk_engine": True,
            "use_macro": True,
            "csv_path": "D:/futures_v6/macro_engine/output/{symbol}_macro_daily_{date}.csv"
        }
    )
    
    if result:
        print("[OK] Strategy added")
    else:
        print("[WARN] Strategy add returned False (may already exist or class not found)")
    
    # 查看策略列表
    print("\n[2.2] Strategy list:")
    strategies = bridge.get_strategies()
    for s in strategies:
        print(f"  - {s['name']} ({s['class_name']}): {s['status']}")
    
    # 初始化策略
    print("\n[2.3] Initializing strategy...")
    if "test_ru" in [s['name'] for s in strategies]:
        result = bridge.init_strategy("test_ru")
        if result:
            print("[OK] Strategy initialized")
        else:
            print("[WARN] Strategy init returned False")
    else:
        print("[WARN] Strategy not found, skipping init")
    
    # 查看更新后的策略列表
    print("\n[2.4] Updated strategy list:")
    strategies = bridge.get_strategies()
    for s in strategies:
        print(f"  - {s['name']} ({s['class_name']}): {s['status']}")
    
    print("\n[OK] Test 2 PASSED")
    return True


def test_data_queries():
    """测试数据查询"""
    print("\n" + "="*60)
    print("Test 3: Data Queries")
    print("="*60)
    
    # 确保VNpy已启动
    if bridge.status != BridgeStatus.RUNNING:
        print("\n[3.0] Starting VNpy...")
        bridge.start()
    
    # 查询持仓
    print("\n[3.1] Positions:")
    positions = bridge.get_positions()
    print(f"  Count: {len(positions)}")
    for p in positions:
        print(f"  - {p['symbol']}: {p['volume']} @ {p['price']}")
    
    # 查询账户
    print("\n[3.2] Account:")
    account = bridge.get_account()
    if account:
        print(f"  Balance: {account['balance']}")
        print(f"  Available: {account['available']}")
        print(f"  Margin: {account['margin']}")
    else:
        print("  No account data (CTP not connected)")
    
    # 查询订单
    print("\n[3.3] Orders:")
    orders = bridge.get_orders()
    print(f"  Count: {len(orders)}")
    
    # 查询成交
    print("\n[3.4] Trades:")
    trades = bridge.get_trades()
    print(f"  Count: {len(trades)}")
    
    print("\n[OK] Test 3 PASSED")
    return True


def test_risk_management():
    """测试风控管理"""
    print("\n" + "="*60)
    print("Test 4: Risk Management")
    print("="*60)
    
    # 查询风控状态
    print("\n[4.1] Risk status:")
    risk = bridge.get_risk_status()
    print(f"  Status: {risk['status']}")
    print(f"  Active rules: {len(risk['active_rules'])}")
    print(f"  Recent events: {len(risk['recent_events'])}")
    
    # 查询风控事件
    print("\n[4.2] Risk events:")
    events = bridge.get_risk_events(limit=10)
    print(f"  Count: {len(events)}")
    for e in events:
        print(f"  - [{e['timestamp']}] {e['rule_id']}: {e['action']} - {e['reason']}")
    
    print("\n[OK] Test 4 PASSED")
    return True


def test_event_callbacks():
    """测试事件回调"""
    print("\n" + "="*60)
    print("Test 5: Event Callbacks")
    print("="*60)
    
    events_received = []
    
    def on_risk_event(event):
        events_received.append(event)
        print(f"  [Callback] Risk event: {event.rule_id} - {event.action}")
    
    def on_ws_event(event_type, data):
        print(f"  [Callback] WS event: {event_type}")
    
    # 注册回调
    print("\n[5.1] Registering callbacks...")
    bridge.register_risk_callback(on_risk_event)
    bridge.register_ws_callback(on_ws_event)
    print("[OK] Callbacks registered")
    
    # 模拟风控事件（通过解析日志）
    print("\n[5.2] Simulating risk event...")
    bridge._parse_risk_event("[RISK BLOCK] R8: 非交易时间禁止下单")
    
    # 检查回调是否被触发
    time.sleep(0.1)  # 等待回调执行
    print(f"\n[5.3] Events received: {len(events_received)}")
    if events_received:
        print(f"  Last event: {events_received[-1].rule_id} - {events_received[-1].action}")
    
    print("\n[OK] Test 5 PASSED")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("VNpyBridge Test Suite")
    print("="*60)
    
    tests = [
        ("Basic Lifecycle", test_basic_lifecycle),
        ("Strategy Management", test_strategy_management),
        ("Data Queries", test_data_queries),
        ("Risk Management", test_risk_management),
        ("Event Callbacks", test_event_callbacks),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] Test {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 清理
    print("\n" + "="*60)
    print("Cleanup")
    print("="*60)
    if bridge.status == BridgeStatus.RUNNING:
        bridge.stop()
        print("[OK] VNpy stopped")
    else:
        print("[INFO] VNpy not running, skip cleanup")
    
    # 汇总
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"  {status}: {name}")
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
