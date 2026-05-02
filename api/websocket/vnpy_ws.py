#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket服务 - 实时推送VNpy数据

提供:
- 持仓变化实时推送
- 账户资金实时推送
- 订单状态实时推送
- 成交记录实时推送
- 风控事件实时推送
- 策略日志实时推送

使用:
    ws = VNpyWebSocket(bridge)
    await ws.start(app)
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from services.vnpy_bridge import VNpyBridge, RiskEvent

logger = logging.getLogger("VNpyWebSocket")


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # 每个连接的订阅类型
    
    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()  # 默认订阅所有
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, event_types: list):
        """订阅事件类型"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(event_types)
    
    def unsubscribe(self, websocket: WebSocket, event_types: list):
        """取消订阅"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(event_types)
    
    async def broadcast(self, event_type: str, data: Any):
        """广播消息给所有订阅者"""
        if not self.active_connections:
            return
        
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        # 发送给订阅了该类型的连接
        disconnected = set()
        for ws in self.active_connections:
            try:
                # 检查是否订阅了该类型（空集合表示订阅所有）
                subs = self.subscriptions.get(ws, set())
                if not subs or event_type in subs:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                disconnected.add(ws)
        
        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_personal(self, websocket: WebSocket, event_type: str, data: Any):
        """发送消息给指定连接"""
        try:
            message = json.dumps({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Personal send error: {e}")
            self.disconnect(websocket)


class VNpyWebSocket:
    """VNpy WebSocket服务"""
    
    def __init__(self, bridge: VNpyBridge):
        self.bridge = bridge
        self.manager = ConnectionManager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self, app: FastAPI):
        """启动WebSocket服务"""
        if self._running:
            return
        
        self._running = True
        
        # 注册桥接回调
        self.bridge.register_ws_callback(self._on_bridge_event)
        self.bridge.register_risk_callback(self._on_risk_event)
        
        # 添加WebSocket路由
        @app.websocket("/ws/vnpy")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            try:
                # 发送初始状态
                await self._send_initial_state(websocket)
                
                # 处理客户端消息
                while self._running:
                    try:
                        data = await websocket.receive_text()
                        await self._handle_client_message(websocket, data)
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        logger.error(f"WebSocket message error: {e}")
                        break
            finally:
                self.manager.disconnect(websocket)
        
        logger.info("WebSocket service started")
    
    async def stop(self):
        """停止WebSocket服务"""
        self._running = False
        
        # 关闭所有连接
        for ws in list(self.manager.active_connections):
            try:
                await ws.close()
            except Exception:
                pass
        
        self.manager.active_connections.clear()
        logger.info("WebSocket service stopped")
    
    async def _send_initial_state(self, websocket: WebSocket):
        """发送初始状态"""
        # 发送当前状态
        await self.manager.send_personal(websocket, "status", self.bridge.get_status())
        
        # 发送持仓
        positions = self.bridge.get_positions()
        if positions:
            await self.manager.send_personal(websocket, "positions", positions)
        
        # 发送账户
        account = self.bridge.get_account()
        if account:
            await self.manager.send_personal(websocket, "account", account)
        
        # 发送策略
        strategies = self.bridge.get_strategies()
        if strategies:
            await self.manager.send_personal(websocket, "strategies", strategies)
    
    async def _handle_client_message(self, websocket: WebSocket, data: str):
        """处理客户端消息"""
        try:
            msg = json.loads(data)
            action = msg.get("action")
            
            if action == "subscribe":
                event_types = msg.get("types", [])
                self.manager.subscribe(websocket, event_types)
                await self.manager.send_personal(websocket, "subscribed", {
                    "types": event_types
                })
            
            elif action == "unsubscribe":
                event_types = msg.get("types", [])
                self.manager.unsubscribe(websocket, event_types)
                await self.manager.send_personal(websocket, "unsubscribed", {
                    "types": event_types
                })
            
            elif action == "ping":
                await self.manager.send_personal(websocket, "pong", {
                    "time": datetime.now().isoformat()
                })
            
            elif action == "get_status":
                await self.manager.send_personal(websocket, "status", self.bridge.get_status())
            
            elif action == "get_positions":
                await self.manager.send_personal(websocket, "positions", self.bridge.get_positions())
            
            elif action == "get_account":
                await self.manager.send_personal(websocket, "account", self.bridge.get_account())
            
            elif action == "get_strategies":
                await self.manager.send_personal(websocket, "strategies", self.bridge.get_strategies())
            
            elif action == "start_strategy":
                name = msg.get("name")
                if name:
                    result = self.bridge.start_strategy(name)
                    await self.manager.send_personal(websocket, "strategy_started", {
                        "name": name,
                        "success": result
                    })
            
            elif action == "stop_strategy":
                name = msg.get("name")
                if name:
                    result = self.bridge.stop_strategy(name)
                    await self.manager.send_personal(websocket, "strategy_stopped", {
                        "name": name,
                        "success": result
                    })
            
            else:
                await self.manager.send_personal(websocket, "error", {
                    "message": f"Unknown action: {action}"
                })
        
        except json.JSONDecodeError:
            await self.manager.send_personal(websocket, "error", {
                "message": "Invalid JSON"
            })
        except Exception as e:
            logger.error(f"Handle message error: {e}")
            await self.manager.send_personal(websocket, "error", {
                "message": str(e)
            })
    
    def _on_bridge_event(self, event_type: str, data: Any):
        """处理桥接事件"""
        # 异步广播
        asyncio.create_task(self.manager.broadcast(event_type, data))
    
    def _on_risk_event(self, event: RiskEvent):
        """处理风控事件"""
        asyncio.create_task(self.manager.broadcast("risk_event", {
            "timestamp": event.timestamp,
            "rule_id": event.rule_id,
            "rule_name": event.rule_name,
            "action": event.action,
            "symbol": event.symbol,
            "direction": event.direction,
            "reason": event.reason
        }))


# 全局WebSocket实例
ws_manager: Optional[VNpyWebSocket] = None


def init_websocket(bridge: VNpyBridge, app: FastAPI):
    """初始化WebSocket服务"""
    global ws_manager
    ws_manager = VNpyWebSocket(bridge)
    
    @app.on_event("startup")
    async def startup():
        await ws_manager.start(app)
    
    @app.on_event("shutdown")
    async def shutdown():
        await ws_manager.stop()
    
    return ws_manager
