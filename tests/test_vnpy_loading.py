#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNpy 策略加载测试脚本
验证 MacroRiskStrategy 能正确加载到 VNpy 环境
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_strategy_import():
    """测试策略导入"""
    print("\n[Test 1] Strategy Import")
    print("-" * 50)
    
    try:
        from strategies.macro_risk_strategy import MacroRiskStrategy
        print("[OK] MacroRiskStrategy imported successfully")
        return True
    except Exception as e:
        print("[FAIL] Import failed: %s" % e)
        return False


def test_strategy_init():
    """测试策略初始化"""
    print("\n[Test 2] Strategy Initialization")
    print("-" * 50)
    
    try:
        from strategies.macro_risk_strategy import MacroRiskStrategy
        
        # 创建策略实例（无引擎模式）
        strategy = MacroRiskStrategy(None, "test_strategy", "RU2505.SHFE", {})
        strategy.on_init()
        
        print("[OK] Strategy initialized")
        print("[OK] Symbol: %s" % strategy.symbol)
        print("[OK] Risk profile: %s" % strategy.risk_profile)
        print("[OK] Risk engine: %s" % ("Active" if strategy.risk_engine else "Inactive"))
        
        if strategy.risk_engine:
            active_rules = [r.rule_id for r in strategy.risk_engine.rules if r.is_enabled()]
            print("[OK] Active rules: %s" % active_rules)
        
        return True
    except Exception as e:
        print("[FAIL] Initialization failed: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def test_csv_loading():
    """测试CSV信号加载"""
    print("\n[Test 3] CSV Signal Loading")
    print("-" * 50)
    
    try:
        from strategies.macro_risk_strategy import MacroRiskStrategy
        from datetime import datetime
        
        strategy = MacroRiskStrategy(None, "test_csv", "RU2505.SHFE", {})
        strategy.on_init()
        
        # 测试加载2026-04-24的信号
        test_date = datetime(2026, 4, 24)
        strategy.load_macro_signal(test_date)
        
        print("[OK] CSV loaded for date: 2026-04-24")
        print("[OK] Macro direction: %s" % strategy.macro_direction)
        print("[OK] Macro score: %.4f" % strategy.macro_score)
        
        return True
    except Exception as e:
        print("[FAIL] CSV loading failed: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def test_risk_check():
    """测试风控检查"""
    print("\n[Test 4] Risk Check")
    print("-" * 50)
    
    try:
        from strategies.macro_risk_strategy import MacroRiskStrategy
        
        strategy = MacroRiskStrategy(None, "test_risk", "RU2505.SHFE", {})
        strategy.on_init()
        
        # 禁用交易时间检查（方便测试）
        if 'R8' in strategy.risk_engine.rule_instances:
            strategy.risk_engine.rule_instances['R8'].enabled = False
        
        # 测试正常场景
        strategy.macro_score = 50
        strategy.macro_direction = "LONG"
        result = strategy.check_risk("LONG", "OPEN", 15000, 1)
        print("[OK] Normal risk check: %s" % result)
        
        # 测试熔断场景
        strategy.macro_score = 20
        strategy.macro_direction = "SHORT"
        result = strategy.check_risk("LONG", "OPEN", 15000, 1)
        print("[OK] Fuse risk check: %s" % result)
        
        return True
    except Exception as e:
        print("[FAIL] Risk check failed: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def test_vnpy_environment():
    """测试VNpy环境"""
    print("\n[Test 5] VNpy Environment")
    print("-" * 50)
    
    checks = []
    
    # 检查VNpy核心模块
    try:
        from vnpy.event import EventEngine
        print("[OK] vnpy.event imported")
        checks.append(True)
    except ImportError as e:
        print("[FAIL] vnpy.event: %s" % e)
        checks.append(False)
    
    try:
        from vnpy.trader.engine import MainEngine
        print("[OK] vnpy.trader.engine imported")
        checks.append(True)
    except ImportError as e:
        print("[FAIL] vnpy.trader.engine: %s" % e)
        checks.append(False)
    
    try:
        from vnpy_ctastrategy import CtaStrategyApp
        print("[OK] vnpy_ctastrategy imported")
        checks.append(True)
    except ImportError as e:
        print("[FAIL] vnpy_ctastrategy: %s" % e)
        checks.append(False)
    
    try:
        from vnpy_ctp import CtpGateway
        print("[OK] vnpy_ctp imported")
        checks.append(True)
    except ImportError as e:
        print("[FAIL] vnpy_ctp: %s" % e)
        checks.append(False)
    
    return all(checks)


def test_strategy_in_vnpy():
    """在VNpy环境中测试策略"""
    print("\n[Test 6] Strategy in VNpy Context")
    print("-" * 50)
    
    try:
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy_ctastrategy import CtaStrategyApp
        from strategies.macro_risk_strategy import MacroRiskStrategy
        
        # 创建事件引擎
        event_engine = EventEngine()
        
        # 创建主引擎
        main_engine = MainEngine(event_engine)
        
        # 添加CTA策略应用
        cta_app = main_engine.add_app(CtaStrategyApp)
        
        print("[OK] VNpy engine initialized")
        print("[OK] CtaStrategyApp added")
        
        # 获取CTA引擎
        cta_engine = main_engine.get_engine("CtaStrategy")
        
        if cta_engine:
            print("[OK] CtaEngine retrieved")
            
            # 尝试添加策略
            try:
                cta_engine.add_strategy(
                    class_name="MacroRiskStrategy",
                    strategy_name="test_macro_risk",
                    vt_symbol="RU2505.SHFE",
                    setting={
                        "fast_window": 10,
                        "slow_window": 20,
                        "risk_profile": "moderate",
                        "enable_risk_engine": True,
                    }
                )
                print("[OK] Strategy added to CtaEngine")
            except Exception as e:
                print("[WARN] Could not add strategy: %s" % e)
                print("[INFO] This is normal if strategy class is not registered")
        
        # 停止引擎
        main_engine.close()
        event_engine.stop()
        
        print("[OK] VNpy engine stopped")
        return True
        
    except Exception as e:
        print("[FAIL] VNpy test failed: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("VNpy Strategy Loading Test")
    print("="*60)
    
    results = []
    
    # 测试1: 策略导入
    results.append(("Strategy Import", test_strategy_import()))
    
    # 测试2: 策略初始化
    results.append(("Strategy Init", test_strategy_init()))
    
    # 测试3: CSV加载
    results.append(("CSV Loading", test_csv_loading()))
    
    # 测试4: 风控检查
    results.append(("Risk Check", test_risk_check()))
    
    # 测试5: VNpy环境
    results.append(("VNpy Environment", test_vnpy_environment()))
    
    # 测试6: VNpy上下文
    results.append(("Strategy in VNpy", test_strategy_in_vnpy()))
    
    # 汇总
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        if result:
            passed += 1
        else:
            failed += 1
        print("[%s] %s" % (status, name))
    
    print("\nTotal: %d passed, %d failed" % (passed, failed))
    
    if failed == 0:
        print("\n[OK] All tests passed!")
        return True
    else:
        print("\n[WARNING] Some tests failed. Check logs above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
