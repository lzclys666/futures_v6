#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacroRiskStrategy 策略加载测试
验证策略能正确加载并运行风控检查
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from strategies.macro_risk_strategy import MacroRiskStrategy, RiskEngine, RiskContext, OrderRequest


def test_strategy_init():
    """测试策略初始化"""
    print("\n[Test 1] Strategy Initialization")
    print("-" * 50)
    
    strategy = MacroRiskStrategy(None, "test", "RU2505.SHFE", {})
    strategy.on_init()
    
    assert strategy.risk_engine is not None, "RiskEngine not initialized"
    assert strategy.risk_profile == "moderate", "Default profile should be moderate"
    
    print("[OK] Strategy initialized")
    print("[OK] RiskEngine active: %d rules" % len([r for r in strategy.risk_engine.rules if r.is_enabled()]))
    return strategy


def test_risk_check_pass(strategy):
    """测试风控通过场景"""
    print("\n[Test 2] Risk Check - PASS")
    print("-" * 50)
    
    # 正常市场环境 - 设置交易时间内的mock
    strategy.macro_score = 50
    strategy.macro_direction = "LONG"
    
    # Mock R8规则（交易时间检查）- 直接设为通过
    if strategy.risk_engine and 'R8' in strategy.risk_engine.rule_instances:
        r8 = strategy.risk_engine.rule_instances['R8']
        r8.enabled = False  # 测试时禁用交易时间检查
    
    result = strategy.check_risk("LONG", "OPEN", 15000, 1)
    
    print("[OK] Risk check result: %s" % result)
    print("[OK] Risk status: %s" % strategy.risk_status)
    
    assert result == True, "Normal order should pass risk check"
    return True


def test_risk_check_block_macro(strategy):
    """测试宏观熔断拦截"""
    print("\n[Test 3] Risk Check - BLOCK (Macro Fuse)")
    print("-" * 50)
    
    # 极端看空环境
    strategy.macro_score = 20
    strategy.macro_direction = "SHORT"
    
    result = strategy.check_risk("LONG", "OPEN", 15000, 1)
    
    print("[OK] Risk check result: %s" % result)
    print("[OK] Risk status: %s" % strategy.risk_status)
    
    assert result == False, "Long order should be blocked in extreme bearish"
    return True


def test_risk_check_block_daily_loss(strategy):
    """测试单日亏损限制拦截"""
    print("\n[Test 4] Risk Check - BLOCK (Daily Loss)")
    print("-" * 50)
    
    # 模拟当日大额亏损
    strategy.macro_score = 50
    strategy.macro_direction = "LONG"
    
    # 构建自定义上下文（大额亏损）
    context = RiskContext(
        account={
            'equity': 100000,
            'available': 80000,
            'used_margin': 15000,
            'frozen': 0,
            'pre_frozen': 0,
            'daily_pnl': -6000,  # 大额亏损
        },
        positions={},
        market_data={'macro_score': 50}
    )
    
    order = OrderRequest('RU', 'SHFE', 'LONG', 'OPEN', 15000, 1)
    results = strategy.risk_engine.check_order(order, context)
    
    blocked = any(r.action.value == 'BLOCK' for r in results)
    print("[OK] Risk check result: %s" % ('BLOCKED' if blocked else 'PASSED'))
    
    for r in results:
        if r.action.value == 'BLOCK':
            print("  -> Blocked by %s: %s" % (r.rule_id, r.message))
    
    assert blocked, "Order should be blocked due to daily loss limit"
    return True


def test_risk_context_building(strategy):
    """测试风控上下文构建"""
    print("\n[Test 5] Risk Context Building")
    print("-" * 50)
    
    context = strategy.build_risk_context(15000)
    
    print("[OK] Account info: %s" % str(context.account))
    print("[OK] Positions: %s" % str(context.positions))
    print("[OK] Market data keys: %s" % list(context.market_data.keys()))
    
    assert context.account is not None, "Account info missing"
    assert 'macro_score' in context.market_data, "Macro score missing"
    
    return True


def test_profile_switching():
    """测试风险画像切换"""
    print("\n[Test 6] Risk Profile Switching")
    print("-" * 50)
    
    profiles = ['conservative', 'moderate', 'aggressive']
    
    for profile in profiles:
        strategy = MacroRiskStrategy(None, "test_%s" % profile, "RU2505.SHFE", {})
        strategy.risk_profile = profile
        strategy.on_init()
        
        r2_config = strategy.risk_engine.config.get('R2', {})
        print("[OK] %s: R2 limit=%s, min=%s" % (profile, r2_config.get('limit'), r2_config.get('absolute_min')))
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("MacroRiskStrategy Integration Test")
    print("="*60)
    
    try:
        # Test 1: 初始化
        strategy = test_strategy_init()
        
        # Test 2: 正常通过
        test_risk_check_pass(strategy)
        
        # Test 3: 宏观熔断拦截
        test_risk_check_block_macro(strategy)
        
        # Test 4: 单日亏损拦截
        test_risk_check_block_daily_loss(strategy)
        
        # Test 5: 上下文构建
        test_risk_context_building(strategy)
        
        # Test 6: 画像切换
        test_profile_switching()
        
        print("\n" + "="*60)
        print("All tests PASSED [OK]")
        print("="*60)
        return True
        
    except AssertionError as e:
        print("\n[FAIL] Test FAILED: %s" % e)
        return False
    except Exception as e:
        print("\n[ERROR] Test ERROR: %s" % e)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
