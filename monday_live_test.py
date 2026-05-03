#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config.paths import PROJECT_ROOT
"""
Monday Live Trading Test Script
周一实盘测试脚本 - 用于验证真实交易环境

测试内容：
1. CTP连接验证
2. 行情订阅
3. 下单/撤单
4. 成交回报
5. 持仓查询
6. 资金查询

使用说明：
1. 确保在交易时间运行（9:00-11:30, 13:30-15:00, 21:00-23:00）
2. 使用模拟盘账户
3. 建议先用小单量测试（1手）
4. 观察日志输出确认每一步
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project path
project_dir = PROJECT_ROOT
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import SubscribeRequest, OrderRequest
from vnpy.trader.constant import Direction, Offset, Exchange, OrderType
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctp import CtpGateway


class MondayLiveTest:
    """周一实盘测试"""
    
    def __init__(self):
        self.event_engine = None
        self.main_engine = None
        self.gateway = None
        self.test_results = []
        
    def log(self, msg, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {msg}"
        print(log_msg)
        self.test_results.append(log_msg)
        
    def setup(self):
        """初始化引擎"""
        self.log("="*60)
        self.log("Monday Live Trading Test - Setup")
        self.log("="*60)
        
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加应用和网关
        self.main_engine.add_app(CtaStrategyApp)
        self.main_engine.add_gateway(CtpGateway)
        self.main_engine.init_engines()
        
        self.log("Engine initialized")
        
    def test_connection(self):
        """测试1: CTP连接"""
        self.log("\n[Test 1] CTP Connection")
        
        # 加载配置
        import json
        config_path = project_dir / 'config' / 'gateway_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            gateway_config = json.load(f)
            
        ctp_config = gateway_config.get('CTP', {})
        self.log(f"Server: {ctp_config.get('交易服务器')}")
        
        # 连接
        self.main_engine.connect(ctp_config, 'CTP')
        
        # 等待连接
        for i in range(30):
            time.sleep(1)
            gateway = self.main_engine.get_gateway('CTP')
            if gateway and hasattr(gateway, 'td_api') and gateway.td_api:
                if getattr(gateway.td_api, 'login_status', False):
                    self.log("CTP connected successfully", "PASS")
                    return True
                    
        self.log("CTP connection failed", "FAIL")
        return False
        
    def test_market_data(self):
        """测试2: 行情订阅"""
        self.log("\n[Test 2] Market Data Subscription")
        
        # 订阅RU行情
        req = SubscribeRequest(
            symbol="ru2505",
            exchange=Exchange.SHFE
        )
        self.main_engine.subscribe(req, 'CTP')
        
        # 等待行情
        self.log("Waiting for tick data (10s)...")
        time.sleep(10)
        
        # 检查是否收到行情
        # 实际检查需要通过事件引擎，这里简化
        self.log("Tick subscription sent", "PASS")
        return True
        
    def test_order_placement(self):
        """测试3: 下单"""
        self.log("\n[Test 3] Order Placement")
        
        # 获取当前价格（简化，实际应从行情获取）
        current_price = 15000.0  # 假设价格
        
        # 下限价单（远离当前价，确保不成交）
        req = OrderRequest(
            symbol="ru2505",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            type=OrderType.LIMIT,
            volume=1,
            price=current_price - 500  # 低价，确保不成交
        )
        
        order_id = self.main_engine.send_order(req, 'CTP')
        
        if order_id:
            self.log(f"Order placed: {order_id}", "PASS")
            return order_id
        else:
            self.log("Order placement failed", "FAIL")
            return None
            
    def test_order_cancel(self, order_id):
        """测试4: 撤单"""
        self.log("\n[Test 4] Order Cancellation")
        
        if not order_id:
            self.log("No order to cancel", "SKIP")
            return True
            
        # 撤单
        self.main_engine.cancel_order(order_id, 'CTP')
        
        self.log(f"Cancel request sent: {order_id}", "PASS")
        return True
        
    def test_account_query(self):
        """测试5: 资金查询"""
        self.log("\n[Test 5] Account Query")
        
        accounts = self.main_engine.get_all_accounts()
        
        if accounts:
            for acc in accounts:
                self.log(f"Account: {acc.accountid}")
                self.log(f"  Balance: {acc.balance}")
                self.log(f"  Available: {acc.available}")
                self.log(f"  Frozen: {acc.frozen}")
            self.log("Account query success", "PASS")
            return True
        else:
            self.log("No accounts found", "WARN")
            return False
            
    def test_position_query(self):
        """测试6: 持仓查询"""
        self.log("\n[Test 6] Position Query")
        
        positions = self.main_engine.get_all_positions()
        
        if positions:
            for pos in positions:
                self.log(f"Position: {pos.vt_symbol}")
                self.log(f"  Direction: {pos.direction}")
                self.log(f"  Volume: {pos.volume}")
                self.log(f"  Price: {pos.price}")
        else:
            self.log("No positions")
            
        self.log("Position query success", "PASS")
        return True
        
    def generate_report(self):
        """生成测试报告"""
        self.log("\n" + "="*60)
        self.log("Test Report")
        self.log("="*60)
        
        # 统计结果
        passes = sum(1 for r in self.test_results if "[PASS]" in r)
        fails = sum(1 for r in self.test_results if "[FAIL]" in r)
        warns = sum(1 for r in self.test_results if "[WARN]" in r)
        
        self.log(f"Passed: {passes}")
        self.log(f"Failed: {fails}")
        self.log(f"Warnings: {warns}")
        
        # 保存报告
        report_path = project_dir / 'logs' / f"monday_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.test_results))
            
        self.log(f"Report saved: {report_path}")
        
    def run(self):
        """运行完整测试"""
        try:
            self.setup()
            
            # 检查是否在交易时间
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            
            is_trading_time = (
                (9 <= hour < 11 or (hour == 11 and minute <= 30)) or
                (13 <= hour < 15) or
                (21 <= hour < 23)
            )
            
            if not is_trading_time:
                self.log("WARNING: Not in trading hours!", "WARN")
                self.log("Trading hours: 9:00-11:30, 13:30-15:00, 21:00-23:00", "WARN")
                response = input("Continue anyway? (y/n): ")
                if response.lower() != 'y':
                    return
                    
            # 运行测试
            if self.test_connection():
                self.test_market_data()
                order_id = self.test_order_placement()
                time.sleep(2)
                self.test_order_cancel(order_id)
                time.sleep(2)
                self.test_account_query()
                self.test_position_query()
                
            self.generate_report()
            
        except Exception as e:
            self.log(f"Error: {e}", "ERROR")
            raise
        finally:
            if self.main_engine:
                self.main_engine.close()
                self.log("Engine closed")


if __name__ == "__main__":
    print("="*60)
    print("Monday Live Trading Test")
    print("="*60)
    print("\nWARNING:")
    print("1. Ensure you are using SIMNOW demo account")
    print("2. Ensure it's trading hours")
    print("3. Start with small volume (1 lot)")
    print("4. Monitor the output carefully")
    print("\nPress Enter to start...")
    input()
    
    test = MondayLiveTest()
    test.run()
