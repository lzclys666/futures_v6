#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNpyBridge - Paper Trading 实现
用于开发和测试环境，不连接真实交易所
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("VNpyBridge.Paper")


@dataclass
class OrderRecord:
    """订单记录"""
    vt_orderid: str
    vt_symbol: str
    direction: str  # LONG / SHORT
    offset: str  # OPEN / CLOSE / CLOSETODAY / CLOSEYESTERDAY
    price: float
    volume: int
    order_type: str = "LIMIT"
    status: str = "submitted"  # submitted, filled, cancelled, rejected
    filled_volume: int = 0
    filled_price: float = 0.0
    submitted_time: str = ""
    
    def __post_init__(self):
        if not self.submitted_time:
            self.submitted_time = datetime.now().isoformat()


@dataclass
class PositionRecord:
    """持仓记录"""
    vt_symbol: str
    direction: str  # LONG / SHORT
    volume: int
    avg_price: float
    last_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_price(self, last_price: float):
        self.last_price = last_price
        self.unrealized_pnl = (last_price - self.avg_price) * self.volume * (1 if self.direction == "LONG" else -1)


class PaperBridge:
    """
    Paper Trading 模式的 VNpyBridge 实现
    模拟订单执行，不连接真实交易所
    """
    
    def __init__(self):
        self._status_value = "running"  # 模拟已启动状态
        self._orders: Dict[str, OrderRecord] = {}
        self._positions: Dict[str, PositionRecord] = {}
        self._order_counter = 0
        self._account = {
            "account_id": "PAPER001",
            "balance": 1000000.0,
            "available": 1000000.0,
            "position_pnl": 0.0,
            "close_pnl": 0.0,
        }
        self._event_loop = None
        self._ws_clients: List[Any] = []
        logger.info("PaperBridge initialized")
    
    @property
    def status(self):
        """返回状态对象（兼容真实 bridge 接口）"""
        class Status:
            value = "running"
        return Status()
    
    def is_running(self) -> bool:
        return True
    
    def is_trading_hours(self) -> bool:
        """检查当前是否在交易时间内"""
        now = datetime.now()
        hour = now.hour
        # 简单模拟：白天交易时段
        return 9 <= hour < 15 or 21 <= hour < 23
    
    def get_account(self) -> Dict:
        """获取账户信息"""
        return self._account.copy()
    
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        return [
            {
                "vt_symbol": pos.vt_symbol,
                "direction": pos.direction,
                "volume": pos.volume,
                "avg_price": pos.avg_price,
                "last_price": pos.last_price,
                "unrealized_pnl": pos.unrealized_pnl,
            }
            for pos in self._positions.values()
        ]
    
    def get_orders(self) -> List[Dict]:
        """获取订单列表"""
        return [
            {
                "vt_orderid": order.vt_orderid,
                "vt_symbol": order.vt_symbol,
                "direction": order.direction,
                "offset": order.offset,
                "price": order.price,
                "volume": order.volume,
                "order_type": order.order_type,
                "status": order.status,
                "filled_volume": order.filled_volume,
                "filled_price": order.filled_price,
                "submitted_time": order.submitted_time,
            }
            for order in self._orders.values()
        ]
    
    def send_order(
        self,
        vt_symbol: str,
        direction: str,
        offset: str,
        price: float,
        volume: int,
        order_type: str = "LIMIT"
    ) -> Optional[str]:
        """
        发送订单（Paper Trading 模拟）
        返回订单ID，失败返回None
        """
        self._order_counter += 1
        vt_orderid = f"{vt_symbol}-{direction}-{self._order_counter:04d}"
        
        order = OrderRecord(
            vt_orderid=vt_orderid,
            vt_symbol=vt_symbol,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            order_type=order_type,
            status="submitted",
        )
        self._orders[vt_orderid] = order
        
        logger.info(f"Paper order sent: {vt_orderid}")
        
        # 模拟立即成交（价格变动 0.1%）
        asyncio.create_task(self._simulate_fill(order))
        
        return vt_orderid
    
    async def _simulate_fill(self, order: OrderRecord):
        """模拟订单成交"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        # 简单模拟：以报价的 0.1% 滑点成交
        slippage = order.price * 0.001
        if order.direction == "LONG":
            fill_price = order.price + slippage
        else:
            fill_price = order.price - slippage
        
        order.status = "filled"
        order.filled_volume = order.volume
        order.filled_price = fill_price
        
        # 更新持仓
        position_key = f"{order.vt_symbol}-{order.direction}"
        if order.offset == "OPEN":
            if position_key in self._positions:
                pos = self._positions[position_key]
                # 重新计算平均价
                total_vol = pos.volume + order.volume
                pos.avg_price = (pos.avg_price * pos.volume + fill_price * order.volume) / total_vol
                pos.volume = total_vol
            else:
                self._positions[position_key] = PositionRecord(
                    vt_symbol=order.vt_symbol,
                    direction=order.direction,
                    volume=order.volume,
                    avg_price=fill_price,
                    last_price=fill_price,
                )
        elif order.offset in ("CLOSE", "CLOSETODAY", "CLOSEYESTERDAY"):
            if position_key in self._positions:
                pos = self._positions[position_key]
                pos.volume -= order.volume
                if pos.volume <= 0:
                    del self._positions[position_key]
        
        # 更新账户
        self._recalc_account()
        
        logger.info(f"Paper order filled: {order.vt_orderid} @ {fill_price}")
    
    def cancel_order(self, vt_orderid: str) -> bool:
        """取消订单"""
        if vt_orderid in self._orders:
            order = self._orders[vt_orderid]
            if order.status == "submitted":
                order.status = "cancelled"
                logger.info(f"Paper order cancelled: {vt_orderid}")
                return True
        return False
    
    def _recalc_account(self):
        """重新计算账户资金"""
        total_pnl = sum(pos.unrealized_pnl for pos in self._positions.values())
        self._account["position_pnl"] = total_pnl
        self._account["available"] = self._account["balance"] + total_pnl
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "status": self._status_value,
            "connected": True,  # Paper 模式始终连接
            "mode": "paper",
        }
    
    def register_ws_client(self, websocket):
        """注册 WebSocket 客户端"""
        self._ws_clients.append(websocket)
    
    def unregister_ws_client(self, websocket):
        """取消注册 WebSocket 客户端"""
        if websocket in self._ws_clients:
            self._ws_clients.remove(websocket)


# 类型别名（供 routes/vnpy.py 类型注解使用）
VNpyBridge = PaperBridge

# 全局单例
print("[DEBUG] Creating PaperBridge instance...")
bridge = PaperBridge()
print(f"[DEBUG] bridge type: {type(bridge)}, class: {bridge.__class__.__name__}")
