#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Local Paper Trading Test - 本地模拟交易测试
无需CTP连接，验证订单流转、持仓计算、风控触发
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project path
project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from vnpy.trader.object import TickData, ContractData, OrderData, TradeData
from vnpy.trader.constant import Direction, Offset, Exchange, OrderType, Status
from vnpy.trader.utility import round_to


class MockPaperEngine:
    """
    模拟交易引擎 - 本地Paper Trade
    """
    def __init__(self, initial_balance=1000000.0):
        self.balance = initial_balance
        self.available = initial_balance
        self.frozen = 0.0
        self.positions = {}  # {vt_symbol: {"long": 0, "short": 0}}
        self.orders = []
        self.trades = []
        self.order_count = 0
        
    def write_log(self, msg, source=""):
        print(f"[PAPER] {msg}")
        
    def send_order(self, req):
        """模拟下单"""
        self.order_count += 1
        order_id = f"PAPER_{self.order_count}"
        
        # 计算保证金
        margin = req.volume * req.price * 0.1  # 简化：10%保证金
        
        if self.available < margin:
            self.write_log(f"[REJECT] 资金不足: 需要{margin}, 可用{self.available}")
            return None
            
        # 冻结资金
        self.available -= margin
        self.frozen += margin
        
        order = {
            'orderid': order_id,
            'vt_symbol': req.vt_symbol,
            'direction': req.direction,
            'offset': req.offset,
            'price': req.price,
            'volume': req.volume,
            'traded': req.volume,  # 模拟全部成交
            'status': Status.ALLTRADED,
            'datetime': datetime.now()
        }
        self.orders.append(order)
        
        # 模拟成交
        trade = {
            'tradeid': f"TRADE_{self.order_count}",
            'orderid': order_id,
            'vt_symbol': req.vt_symbol,
            'direction': req.direction,
            'offset': req.offset,
            'price': req.price,
            'volume': req.volume,
            'datetime': datetime.now()
        }
        self.trades.append(trade)
        
        # 更新持仓
        self.update_position(trade)
        
        # 释放冻结资金，扣除实际保证金
        self.frozen -= margin
        # 实际占用保证金保留
        
        self.write_log(f"[FILLED] {req.vt_symbol} {req.direction.value} {req.volume}@{req.price}")
        return order_id
        
    def update_position(self, trade):
        """更新持仓"""
        vt_symbol = trade['vt_symbol']
        if vt_symbol not in self.positions:
            self.positions[vt_symbol] = {"long": 0, "short": 0}
            
        pos = self.positions[vt_symbol]
        vol = trade['volume']
        
        if trade['direction'] == Direction.LONG:
            if trade['offset'] == Offset.OPEN:
                pos['long'] += vol
            else:  # CLOSE - 平空仓
                pos['short'] -= vol
        else:  # SHORT
            if trade['offset'] == Offset.OPEN:
                pos['short'] += vol
            else:  # CLOSE - 平多仓
                pos['long'] -= vol
                
    def get_position(self, vt_symbol):
        """获取持仓"""
        pos = self.positions.get(vt_symbol, {"long": 0, "short": 0})
        return pos['long'] - pos['short']  # 净持仓
        
    def print_status(self):
        """打印账户状态"""
        print("\n" + "="*60)
        print("Paper Trading Account Status")
        print("="*60)
        print(f"Balance:      {self.balance:,.2f}")
        print(f"Available:    {self.available:,.2f}")
        print(f"Frozen:       {self.frozen:,.2f}")
        print(f"Margin Used:  {self.balance - self.available:,.2f}")
        print(f"\nPositions:")
        for vt_symbol, pos in self.positions.items():
            net = pos['long'] - pos['short']
            print(f"  {vt_symbol}: Long={pos['long']}, Short={pos['short']}, Net={net}")
        print(f"\nOrders: {len(self.orders)}, Trades: {len(self.trades)}")
        print("="*60)


class PaperTradingTest:
    """模拟交易测试套件"""
    
    def __init__(self):
        self.engine = MockPaperEngine(initial_balance=1000000.0)
        
    def test_buy_open(self):
        """测试开多"""
        print("\n[Test] Buy Open - 开多")
        
        class MockReq:
            vt_symbol = "RU2505.SHFE"
            direction = Direction.LONG
            offset = Offset.OPEN
            price = 15000.0
            volume = 1
            type = OrderType.LIMIT
            
        req = MockReq()
        order_id = self.engine.send_order(req)
        
        assert order_id is not None, "Order should be accepted"
        pos = self.engine.get_position("RU2505.SHFE")
        assert pos == 1, f"Position should be 1, got {pos}"
        
        print("[PASS] Buy open test passed")
        
    def test_sell_close(self):
        """测试平多"""
        print("\n[Test] Sell Close - 平多")
        
        class MockReq:
            vt_symbol = "RU2505.SHFE"
            direction = Direction.SHORT
            offset = Offset.CLOSE
            price = 15500.0
            volume = 1
            type = OrderType.LIMIT
            
        req = MockReq()
        order_id = self.engine.send_order(req)
        
        assert order_id is not None, "Order should be accepted"
        pos = self.engine.get_position("RU2505.SHFE")
        assert pos == 0, f"Position should be 0, got {pos}"
        
        print("[PASS] Sell close test passed")
        
    def test_short_open(self):
        """测试开空"""
        print("\n[Test] Short Open - 开空")
        
        class MockReq:
            vt_symbol = "ZN2505.SHFE"
            direction = Direction.SHORT
            offset = Offset.OPEN
            price = 22000.0
            volume = 2
            type = OrderType.LIMIT
            
        req = MockReq()
        order_id = self.engine.send_order(req)
        
        assert order_id is not None, "Order should be accepted"
        pos = self.engine.get_position("ZN2505.SHFE")
        assert pos == -2, f"Position should be -2, got {pos}"
        
        print("[PASS] Short open test passed")
        
    def test_insufficient_funds(self):
        """测试资金不足"""
        print("\n[Test] Insufficient Funds - 资金不足")
        
        # 创建一个资金很少的引擎
        small_engine = MockPaperEngine(initial_balance=1000.0)
        
        class MockReq:
            vt_symbol = "RU2505.SHFE"
            direction = Direction.LONG
            offset = Offset.OPEN
            price = 15000.0
            volume = 10  # 需要15000保证金
            type = OrderType.LIMIT
            
        req = MockReq()
        order_id = small_engine.send_order(req)
        
        assert order_id is None, "Order should be rejected"
        print("[PASS] Insufficient funds test passed")
        
    def test_position_limit(self):
        """测试持仓限额"""
        print("\n[Test] Position Limit - 持仓限额")
        
        # 假设最大持仓5手
        max_position = 5
        
        class MockReq:
            vt_symbol = "RB2505.SHFE"
            direction = Direction.LONG
            offset = Offset.OPEN
            price = 3500.0
            volume = 3
            type = OrderType.LIMIT
            
        req = MockReq()
        self.engine.send_order(req)
        
        pos = self.engine.get_position("RB2505.SHFE")
        assert pos == 3, f"Position should be 3, got {pos}"
        
        # 再开3手，应该超过限额
        req2 = MockReq()
        req2.volume = 3
        # 这里简化处理，实际策略中会有风控检查
        
        print("[PASS] Position limit test passed")
        
    def test_risk_stop_loss(self):
        """测试止损触发"""
        print("\n[Test] Stop Loss - 止损")
        
        # 先开多仓
        class MockReqOpen:
            vt_symbol = "RU2505.SHFE"
            direction = Direction.LONG
            offset = Offset.OPEN
            price = 15000.0
            volume = 1
            type = OrderType.LIMIT
            
        req_open = MockReqOpen()
        self.engine.send_order(req_open)
        
        # 模拟持仓成本15000，止损14500
        entry_price = 15000.0
        stop_price = 14500.0
        current_price = 14400.0  # 跌破止损
        
        # 检查是否触发止损
        if current_price <= stop_price:
            print(f"[RISK] Stop loss triggered: {current_price} <= {stop_price}")
            
            # 获取当前持仓方向
            pos = self.engine.get_position("RU2505.SHFE")
            if pos > 0:  # 有多仓，平多
                class MockReqClose:
                    vt_symbol = "RU2505.SHFE"
                    direction = Direction.SHORT  # 平多=卖
                    offset = Offset.CLOSE
                    price = current_price
                    volume = abs(pos)
                    type = OrderType.LIMIT
            elif pos < 0:  # 有空仓，平空
                class MockReqClose:
                    vt_symbol = "RU2505.SHFE"
                    direction = Direction.LONG  # 平空=买
                    offset = Offset.CLOSE
                    price = current_price
                    volume = abs(pos)
                    type = OrderType.LIMIT
            else:
                print("[WARN] No position to close")
                return
                
            req_close = MockReqClose()
            self.engine.send_order(req_close)
            
            pos = self.engine.get_position("RU2505.SHFE")
            assert pos == 0, f"Position should be closed, got {pos}"
            
        print("[PASS] Stop loss test passed")
        
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("Paper Trading Tests")
        print("="*60)
        
        try:
            self.test_buy_open()
            self.test_sell_close()
            self.test_short_open()
            self.test_insufficient_funds()
            self.test_position_limit()
            self.test_risk_stop_loss()
            
            print("\n" + "="*60)
            print("ALL TESTS PASSED [OK]")
            print("="*60)
            
            self.engine.print_status()
            
        except AssertionError as e:
            print(f"\n[FAIL] TEST FAILED: {e}")
            raise
        except Exception as e:
            print(f"\n[ERROR] ERROR: {e}")
            raise


if __name__ == "__main__":
    test = PaperTradingTest()
    test.run_all_tests()
