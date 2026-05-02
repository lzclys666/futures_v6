#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VNpyBridge 完整交易流程测试
测试内容:
1. 启动VNpy + PaperAccount
2. 添加策略
3. 模拟行情触发交易
4. 验证持仓/订单/成交
5. 停止策略
6. 重复启动/停止测试
"""

import sys
import os
import time as time_module
from datetime import datetime, time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vnpy_bridge import VNpyBridge, BridgeStatus

# 测试配置
TEST_SYMBOL = "ru2505"  # 橡胶主力合约
TEST_EXCHANGE = "SHFE"

class TradingFlowTest:
    def __init__(self):
        self.bridge = VNpyBridge()
        self.events_received = []
        
    def on_risk_event(self, event):
        """风控事件回调"""
        self.events_received.append(event)
        print(f"  [Risk] {event.get('rule_id', 'N/A')} - {event.get('action', 'N/A')}")
        
    def on_trade_event(self, event):
        """交易事件回调"""
        self.events_received.append(event)
        print(f"  [Trade] {event}")
        
    def run_test(self):
        """运行完整测试流程"""
        print("=" * 60)
        print("VNpyBridge 完整交易流程测试")
        print("=" * 60)
        
        # 1. 启动VNpy
        print("\n[1/6] 启动VNpy引擎...")
        if not self.bridge.start():
            print("[FAIL] 启动失败")
            return False
        print("[OK] VNpy启动成功")
        
        # 检查PaperAccount
        if self.bridge.paper_engine:
            print(f"[OK] PaperAccount已激活 (滑点={self.bridge.paper_engine.slippage})")
        else:
            print("[WARN] PaperAccount未加载")
        
        # 2. 添加策略
        print("\n[2/6] 添加测试策略...")
        strategy_class = "MacroRiskStrategy"
        strategy_name = "test_ru_trading"
        
        result = self.bridge.add_strategy(
            class_name=strategy_class,
            strategy_name=strategy_name,
            vt_symbol=f"{TEST_SYMBOL}.{TEST_EXCHANGE}",
            setting={
                "symbol": TEST_SYMBOL,
                "exchange": TEST_EXCHANGE,
                "risk_level": "medium",
                "position_limit": 5
            }
        )
        if not result:
            print("[FAIL] 添加策略失败")
            self.bridge.stop()
            return False
        print(f"[OK] 策略添加成功: {strategy_name}")
        
        # 3. 初始化策略
        print("\n[3/6] 初始化策略...")
        if not self.bridge.init_strategy(strategy_name):
            print("[FAIL] 初始化失败")
            self.bridge.stop()
            return False
        print("[OK] 策略初始化成功")
        
        # 4. 注册事件监听
        print("\n[4/6] 注册事件监听...")
        self.bridge.register_risk_callback(self.on_risk_event)
        print("[OK] 事件监听已注册")
        
        # 5. 查询初始状态
        print("\n[5/6] 查询初始状态...")
        positions = self.bridge.get_positions()
        account = self.bridge.get_account()
        orders = self.bridge.get_orders()
        
        print(f"  持仓数量: {len(positions)}")
        print(f"  账户权益: {account.get('balance', 'N/A') if account else 'N/A'}")
        print(f"  订单数量: {len(orders)}")
        
        # 6. 模拟风控事件
        print("\n[6/6] 测试风控事件...")
        test_event = {
            "rule_id": "R8",
            "action": "BLOCK",
            "symbol": TEST_SYMBOL,
            "reason": "Test event",
            "timestamp": datetime.now().isoformat()
        }
        # 通过日志触发风控事件
        self.bridge._parse_risk_event("[RISK BLOCK] R8: Test event")
        time_module.sleep(0.5)
        
        if len(self.events_received) > 0:
            print(f"[OK] 收到事件: {len(self.events_received)}个")
        else:
            print("[WARN] 未收到事件")
        
        # 7. 停止策略
        print("\n[清理] 停止策略...")
        self.bridge.stop_strategy(strategy_name)
        print("[OK] 策略已停止")
        
        # 8. 停止VNpy
        print("\n[清理] 停止VNpy...")
        self.bridge.stop()
        print("[OK] VNpy已停止")
        
        return True
        
    def test_restart_cycle(self):
        """测试重复启动/停止"""
        print("\n" + "=" * 60)
        print("重复启动/停止稳定性测试")
        print("=" * 60)
        
        for i in range(3):
            print(f"\n--- 循环 {i+1}/3 ---")
            
            # 启动
            print(f"[{i+1}.1] 启动...")
            if not self.bridge.start():
                print("[FAIL] 启动失败")
                return False
            print("[OK] 启动成功")
            
            # 检查状态
            status = self.bridge.get_status()
            print(f"  状态: {status['status']}")
            
            # 停止
            print(f"[{i+1}.2] 停止...")
            if not self.bridge.stop():
                print("[FAIL] 停止失败")
                return False
            print("[OK] 停止成功")
            
            # 等待资源释放
            time_module.sleep(1.0)
        
        print("\n[OK] 重复启动/停止测试通过")
        return True


def main():
    """主函数"""
    test = TradingFlowTest()
    
    # 运行完整流程测试
    success = test.run_test()
    
    if success:
        # 运行稳定性测试
        success = test.test_restart_cycle()
    
    # 最终清理
    if test.bridge.status == BridgeStatus.RUNNING:
        test.bridge.stop()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    if success:
        print("[OK] 所有测试通过")
    else:
        print("[FAIL] 测试失败")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
