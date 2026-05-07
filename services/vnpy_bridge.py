#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNpyBridge - VNpy与FastAPI的桥接服务

提供:
1. VNpy引擎生命周期管理(启动/停止)
2. 策略管理(添加/初始化/启动/停止)
3. 持仓/账户/订单查询
4. 事件订阅与转发
5. WebSocket实时推送

使用示例:
    bridge = VNpyBridge()
    bridge.start()
    bridge.add_strategy("MacroRiskStrategy", "test_ru", "RU2505.SHFE", {})
    bridge.init_strategy("test_ru")
    bridge.start_strategy("test_ru")
    positions = bridge.get_positions()
    bridge.stop()
"""

import asyncio
import json
import threading
import time as time_module
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

# VNpy导入
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import (
    OrderRequest, CancelRequest, SubscribeRequest,
    ContractData, OrderData, TradeData, PositionData, AccountData
)
from vnpy.trader.constant import Direction, Offset, Exchange, OrderType
from vnpy.trader.utility import extract_vt_symbol

# CTA策略
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctastrategy.base import EVENT_CTA_LOG

# Paper Account
try:
    from vnpy_paperaccount import PaperAccountApp
    HAS_PAPER_ACCOUNT = True
except ImportError:
    HAS_PAPER_ACCOUNT = False
    PaperAccountApp = None

# CTP网关
from vnpy_ctp import CtpGateway

# 风控相关
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VNpyBridge")


class BridgeStatus(Enum):
    """桥接状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class StrategyInfo:
    """策略信息"""
    name: str
    class_name: str
    vt_symbol: str
    status: str = "stopped"  # stopped, initializing, initialized, starting, trading, stopping
    params: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    pos: int = 0
    last_error: Optional[str] = None


@dataclass
class RiskEvent:
    """风控事件"""
    timestamp: str
    rule_id: str
    rule_name: str
    action: str  # BLOCK, WARN, PASS
    symbol: str
    direction: str
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)


class VNpyBridge:
    """
    VNpy桥接服务

    单例模式,确保全局只有一个VNpy引擎实例
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.status = BridgeStatus.STOPPED
        self.event_engine: Optional[EventEngine] = None
        self.main_engine: Optional[MainEngine] = None
        self.cta_engine = None
        self.paper_engine = None

        # 策略管理
        self.strategies: Dict[str, StrategyInfo] = {}

        # 数据缓存
        self.positions: Dict[str, PositionData] = {}
        self.orders: Dict[str, OrderData] = {}
        self.trades: List[TradeData] = []
        self.account: Optional[AccountData] = None

        # 风控事件
        self.risk_events: List[RiskEvent] = []
        self.risk_callbacks: List[Callable[[RiskEvent], None]] = []

        # WebSocket客户端管理
        self._ws_clients: Set[Any] = set()
        self._ws_lock = threading.Lock()

        # 事件循环(用于WebSocket推送)
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_callbacks: List[Callable[[str, Any], None]] = []

        # 启动锁
        self._start_lock = threading.Lock()

        # vt_orderid → order_uuid 映射表（用于对账引擎）
        self._vt_orderid_to_order_uuid: Dict[str, str] = {}

        logger.info("VNpyBridge initialized")

    def start(self) -> bool:
        """
        启动VNpy引擎

        Returns:
            bool: 是否启动成功
        """
        if self.status == BridgeStatus.RUNNING:
            logger.warning("VNpy already running")
            return True

        # 如果之前启动过,需要完全清理
        if self.status in [BridgeStatus.ERROR, BridgeStatus.STOPPED, BridgeStatus.STOPPING]:
            self._cleanup()
            # 额外等待确保资源释放
            time_module.sleep(1.0)

        try:
            self.status = BridgeStatus.STARTING
            logger.info("Starting VNpy engine...")

            # 1. 创建新的事件引擎实例(但不要启动,让MainEngine来启动)
            self.event_engine = EventEngine()
            logger.info("EventEngine created (not started yet)")

            # 2. 创建主引擎 - MainEngine内部会调用event_engine.start()
            self.main_engine = MainEngine(self.event_engine)
            logger.info("MainEngine created")

            # 3. 添加Paper Account
            if HAS_PAPER_ACCOUNT:
                self.main_engine.add_app(PaperAccountApp)
                self.paper_engine = self.main_engine.get_engine("PaperAccount")
                if self.paper_engine:
                    self.paper_engine.active = True
                    self.paper_engine.slippage = 1
                    logger.info("PaperAccount activated (slippage=1)")
            else:
                logger.warning("PaperAccount not installed, skipping")

            # 4. 添加CTP网关
            self.main_engine.add_gateway(CtpGateway)
            logger.info("CtpGateway added")

            # 5. 添加CTA策略
            self.main_engine.add_app(CtaStrategyApp)
            self.cta_engine = self.main_engine.get_engine("CtaStrategy")
            logger.info("CtaStrategyApp added")

            # 6. 注册事件监听
            self._register_events()

            # 7. 加载自定义策略类
            self._load_strategy_classes()

            self.status = BridgeStatus.RUNNING
            logger.info("VNpy engine started successfully")
            return True

        except Exception as e:
            self.status = BridgeStatus.ERROR
            logger.error(f"Failed to start VNpy: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _load_strategy_classes(self):
        """加载自定义策略类到VNpy CTA引擎"""
        if not self.cta_engine:
            return

        try:
            # 方法1: 从strategies包导入
            import importlib
            import sys
            import os

            # 添加项目根目录到路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            # 尝试导入策略模块
            try:
                from strategies.macro_risk_strategy import MacroRiskStrategy
                # 注册到CTA引擎的策略类字典
                if hasattr(self.cta_engine, 'classes'):
                    self.cta_engine.classes['MacroRiskStrategy'] = MacroRiskStrategy
                    logger.info("MacroRiskStrategy loaded into CTA engine (method 1)")
                elif hasattr(self.cta_engine, 'strategy_classes'):
                    self.cta_engine.strategy_classes['MacroRiskStrategy'] = MacroRiskStrategy
                    logger.info("MacroRiskStrategy loaded into CTA engine (method 2)")
                else:
                    logger.warning("CTA engine has no strategy class registry")
            except ImportError as e:
                logger.warning(f"Could not import MacroRiskStrategy: {e}")

            # 方法2: 扫描strategies目录
            strategies_dir = os.path.join(project_root, 'strategies')
            if os.path.exists(strategies_dir):
                for filename in os.listdir(strategies_dir):
                    if filename.endswith('_strategy.py') and not filename.startswith('__'):
                        module_name = f"strategies.{filename[:-3]}"
                        try:
                            module = importlib.import_module(module_name)
                            # 查找策略类
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and
                                    attr_name.endswith('Strategy') and
                                    attr_name != 'CtaTemplate'):
                                    # 注册到CTA引擎
                                    if hasattr(self.cta_engine, 'classes'):
                                        self.cta_engine.classes[attr_name] = attr
                                    elif hasattr(self.cta_engine, 'strategy_classes'):
                                        self.cta_engine.strategy_classes[attr_name] = attr
                                    logger.info(f"Strategy loaded: {attr_name}")
                        except Exception as e:
                            logger.warning(f"Failed to load {module_name}: {e}")

        except Exception as e:
            logger.error(f"Strategy loading error: {e}")

    def _cleanup(self):
        """清理资源"""
        logger.info("Cleaning up resources...")

        # 停止所有策略
        if self.cta_engine:
            try:
                for name in list(self.strategies.keys()):
                    try:
                        self.cta_engine.stop_strategy(name)
                    except Exception:
                        pass
            except Exception:
                pass

        # 关闭主引擎
        if self.main_engine:
            try:
                self.main_engine.close()
            except Exception:
                pass
            self.main_engine = None

        # 停止事件引擎 - 关键:必须停止,否则线程残留
        if self.event_engine:
            try:
                self.event_engine.stop()
                time_module.sleep(0.5)
            except Exception:
                pass
            self.event_engine = None

        self.cta_engine = None
        self.paper_engine = None

        # 清空缓存
        self.positions.clear()
        self.orders.clear()
        self.trades.clear()
        self.account = None
        self.strategies.clear()

        # 强制垃圾回收,确保旧线程资源释放
        import gc
        gc.collect()
        time_module.sleep(0.2)

        logger.info("Cleanup completed")

    def stop(self) -> bool:
        """
        停止VNpy引擎

        Returns:
            bool: 是否停止成功
        """
        if self.status == BridgeStatus.STOPPED:
            return True

        try:
            self.status = BridgeStatus.STOPPING
            logger.info("Stopping VNpy engine...")

            # 停止所有策略
            if self.cta_engine:
                for name in list(self.strategies.keys()):
                    try:
                        self.cta_engine.stop_strategy(name)
                    except Exception:
                        pass
            self.strategies.clear()

            # 关闭主引擎
            if self.main_engine:
                try:
                    self.main_engine.close()
                except Exception:
                    pass
                self.main_engine = None

            # 停止事件引擎
            if self.event_engine:
                try:
                    self.event_engine.stop()
                    time_module.sleep(0.5)
                except Exception:
                    pass
                self.event_engine = None

            self.cta_engine = None
            self.paper_engine = None

            # 清空缓存
            self.positions.clear()
            self.orders.clear()
            self.trades.clear()
            self.account = None

            # 强制垃圾回收
            import gc
            gc.collect()
            time_module.sleep(0.2)

            self.status = BridgeStatus.STOPPED
            logger.info("VNpy engine stopped")
            return True

        except Exception as e:
            self.status = BridgeStatus.ERROR
            logger.error(f"Error stopping VNpy: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _register_events(self):
        """注册事件监听"""
        if not self.event_engine:
            return

        # 注册CTA日志事件
        self.event_engine.register(EVENT_CTA_LOG, self._on_cta_log)

        # 注册通用交易事件
        self.event_engine.register("eOrder", self._on_order)
        self.event_engine.register("eTrade", self._on_trade)
        self.event_engine.register("ePosition", self._on_position)
        self.event_engine.register("eAccount", self._on_account)

        logger.info("Events registered")

    def _on_cta_log(self, event: Event):
        """处理CTA日志事件"""
        log = event.data
        msg = log.msg if hasattr(log, 'msg') else str(log)

        # 解析风控事件
        if "RISK BLOCK" in msg or "RISK WARN" in msg:
            self._parse_risk_event(msg)

        # 转发到WebSocket
        self._emit_ws("log", {
            "time": datetime.now().isoformat(),
            "level": log.levelname if hasattr(log, 'levelname') else 'INFO',
            "message": msg
        })

    def _parse_risk_event(self, msg: str):
        """解析风控事件"""
        try:
            # 格式: [RISK BLOCK] R{rule_id}: {reason}
            if "RISK BLOCK" in msg:
                parts = msg.split("]")
                if len(parts) >= 2:
                    rule_part = parts[1].strip()
                    rule_id = rule_part.split(":")[0].strip() if ":" in rule_part else ""
                    reason = rule_part.split(":", 1)[1].strip() if ":" in rule_part else rule_part

                    event = RiskEvent(
                        timestamp=datetime.now().isoformat(),
                        rule_id=rule_id,
                        rule_name=self._get_rule_name(rule_id),
                        action="BLOCK",
                        symbol="",
                        direction="",
                        reason=reason
                    )

                    self.risk_events.append(event)

                    # 触发回调
                    for cb in self.risk_callbacks:
                        try:
                            cb(event)
                        except Exception as e:
                            logger.error(f"Risk callback error: {e}")

                    # WebSocket推送
                    self._emit_ws("risk_event", {
                        "timestamp": event.timestamp,
                        "rule_id": event.rule_id,
                        "rule_name": event.rule_name,
                        "action": event.action,
                        "reason": event.reason
                    })

        except Exception as e:
            logger.error(f"Parse risk event error: {e}")

    def _get_rule_name(self, rule_id: str) -> str:
        """获取规则名称"""
        rule_names = {
            "R1": "交易权限检查",
            "R2": "单笔亏损限制",
            "R3": "日内回撤限制",
            "R4": "保证金使用率上限",
            "R5": "宏观评分熔断",
            "R6": "宏观方向冲突",
            "R7": "连续亏损暂停",
            "R8": "交易时间检查",
            "R9": "订单频率限制",
            "R10": "品种宏观评分过滤",
            "R11": "品种持仓上限"
        }
        return rule_names.get(rule_id, rule_id)

    def _on_order(self, event: Event):
        """处理订单事件"""
        order = event.data
        self.orders[order.orderid] = order
        self._emit_ws("order", {
            "orderid": order.orderid,
            "symbol": order.symbol,
            "direction": order.direction.value,
            "offset": order.offset.value,
            "price": order.price,
            "volume": order.volume,
            "traded": order.traded,
            "status": order.status.value,
            "time": order.time
        })

    def _on_trade(self, event: Event):
        """处理成交事件"""
        trade = event.data
        self.trades.append(trade)

        # 集成对账引擎：record_trade
        try:
            from services.reconciliation_engine import get_reconciliation_engine
            engine = get_reconciliation_engine()
            ref_order_uuid = self._vt_orderid_to_order_uuid.get(trade.orderid, "")
            engine.record_trade({
                "ref_order_uuid": ref_order_uuid,
                "vt_tradeid": trade.tradeid,
                "symbol": trade.symbol,
                "exchange": trade.exchange.value,
                "direction": trade.direction.value,
                "offset": trade.offset.value,
                "price": float(trade.price),
                "volume": int(trade.volume),
                "trade_time": trade.datetime.strftime("%Y-%m-%dT%H:%M:%S+08:00") if hasattr(trade, 'datetime') and trade.datetime else datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "source": "ctp",
            })
        except Exception as e:
            logger.warning(f"[Reconciliation] record_trade failed: {e}")

        self._emit_ws("trade", {
            "tradeid": trade.tradeid,
            "orderid": trade.orderid,
            "symbol": trade.symbol,
            "direction": trade.direction.value,
            "offset": trade.offset.value,
            "price": trade.price,
            "volume": trade.volume,
            "time": trade.time
        })

    def _on_position(self, event: Event):
        """处理持仓事件"""
        position = event.data
        key = f"{position.symbol}.{position.exchange.value}"
        self.positions[key] = position
        self._emit_ws("position", {
            "symbol": position.symbol,
            "exchange": position.exchange.value,
            "direction": position.direction.value,
            "volume": position.volume,
            "price": position.price,
            "pnl": position.pnl
        })

    def _on_account(self, event: Event):
        """处理账户事件"""
        account = event.data
        self.account = account
        self._emit_ws("account", {
            "accountid": account.accountid,
            "balance": account.balance,
            "available": account.available,
            "frozen": account.frozen,
            "gateway_name": account.gateway_name
        })

    def _emit_ws(self, event_type: str, data: Any):
        """触发WebSocket推送(回调节点 + 直接WebSocket客户端)"""
        # 1. 触发回调
        for cb in self._ws_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")

        # 2. 推送到直接WebSocket客户端
        if self._ws_clients and self._event_loop and self._event_loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._push_to_clients(event_type, data),
                    self._event_loop
                )
            except Exception as e:
                logger.debug(f"WS direct push skipped: {e}")

    # ==================== 策略管理 ====================

    def add_strategy(self, class_name: str, strategy_name: str,
                     vt_symbol: str, setting: Dict[str, Any]) -> bool:
        """
        添加策略

        Args:
            class_name: 策略类名
            strategy_name: 策略实例名
            vt_symbol: 合约代码
            setting: 策略参数

        Returns:
            bool: 是否添加成功
        """
        if not self.cta_engine:
            logger.error("CTA engine not initialized")
            return False

        try:
            self.cta_engine.add_strategy(
                class_name=class_name,
                strategy_name=strategy_name,
                vt_symbol=vt_symbol,
                setting=setting
            )

            self.strategies[strategy_name] = StrategyInfo(
                name=strategy_name,
                class_name=class_name,
                vt_symbol=vt_symbol,
                status="stopped",
                params=setting
            )

            logger.info(f"Strategy added: {strategy_name} ({class_name})")
            return True

        except Exception as e:
            logger.error(f"Add strategy failed: {e}")
            return False

    def init_strategy(self, strategy_name: str) -> bool:
        """
        初始化策略

        Args:
            strategy_name: 策略实例名

        Returns:
            bool: 是否初始化成功
        """
        if not self.cta_engine:
            return False

        try:
            self.cta_engine.init_strategy(strategy_name)

            if strategy_name in self.strategies:
                self.strategies[strategy_name].status = "initialized"

            logger.info(f"Strategy initialized: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Init strategy failed: {e}")
            if strategy_name in self.strategies:
                self.strategies[strategy_name].last_error = str(e)
            return False

    def start_strategy(self, strategy_name: str) -> bool:
        """
        启动策略

        Args:
            strategy_name: 策略实例名

        Returns:
            bool: 是否启动成功
        """
        if not self.cta_engine:
            return False

        try:
            self.cta_engine.start_strategy(strategy_name)

            if strategy_name in self.strategies:
                self.strategies[strategy_name].status = "trading"

            logger.info(f"Strategy started: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Start strategy failed: {e}")
            return False

    def stop_strategy(self, strategy_name: str) -> bool:
        """
        停止策略

        Args:
            strategy_name: 策略实例名

        Returns:
            bool: 是否停止成功
        """
        if not self.cta_engine:
            return False

        try:
            self.cta_engine.stop_strategy(strategy_name)

            if strategy_name in self.strategies:
                self.strategies[strategy_name].status = "stopped"

            logger.info(f"Strategy stopped: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Stop strategy failed: {e}")
            return False

    def edit_strategy(self, strategy_name: str, setting: Dict[str, Any]) -> bool:
        """
        编辑策略参数

        Args:
            strategy_name: 策略实例名
            setting: 新参数

        Returns:
            bool: 是否编辑成功
        """
        if not self.cta_engine:
            return False

        try:
            self.cta_engine.edit_strategy(strategy_name, setting)

            if strategy_name in self.strategies:
                self.strategies[strategy_name].params.update(setting)

            logger.info(f"Strategy edited: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Edit strategy failed: {e}")
            return False

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        移除策略

        Args:
            strategy_name: 策略实例名

        Returns:
            bool: 是否移除成功
        """
        if not self.cta_engine:
            return False

        try:
            # 先停止
            self.stop_strategy(strategy_name)

            # 移除
            self.cta_engine.remove_strategy(strategy_name)

            if strategy_name in self.strategies:
                del self.strategies[strategy_name]

            logger.info(f"Strategy removed: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Remove strategy failed: {e}")
            return False

    # ==================== 数据查询 ====================

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        获取持仓列表

        Returns:
            List[Dict]: 持仓数据列表
        """
        result = []
        for key, pos in self.positions.items():
            result.append({
                "symbol": pos.symbol,
                "exchange": pos.exchange.value,
                "direction": pos.direction.value,
                "volume": pos.volume,
                "price": pos.price,
                "pnl": pos.pnl,
                "yd_volume": pos.yd_volume
            })
        return result

    def get_account(self) -> Optional[Dict[str, Any]]:
        """
        获取账户信息

        Returns:
            Dict: 账户数据
        """
        if not self.account:
            return None

        return {
            "accountid": self.account.accountid,
            "balance": self.account.balance,
            "available": self.account.available,
            "frozen": self.account.frozen,
            "commission": self.account.commission,
            "margin": self.account.margin,
            "gateway_name": self.account.gateway_name
        }

    def get_portfolio(self) -> Dict[str, Any]:
        """
        返回聚合的组合数据(用于前端 PortfolioData)
        包含账户统计 + 持仓列表
        """
        account = self.get_account()
        positions = self.get_positions()

        balance = account.get("balance", 0.0) if account else 0.0
        available = account.get("available", balance) if account else balance

        # 计算浮动盈亏合计
        total_unrealized_pnl = sum(p.get("pnl", 0) for p in positions)

        # 日初权益需要持久化存储,此处简化:当日 unrealized PnL 叠加到权益估算
        starting = getattr(self, "_starting_balance", None)
        if starting is None:
            self._starting_balance = balance
            starting = balance
        daily_pnl = total_unrealized_pnl  # 简化:当日浮动盈亏近似日盈亏
        daily_return = (daily_pnl / starting) if starting > 0 else 0.0

        # 持仓保证金估算
        total_position_value = sum(
            p.get("price", 0) * p.get("volume", 0) * 10 for p in positions
        )
        total_position_pct = (total_position_value / balance) if balance > 0 else 0.0

        return {
            "date": "",
            "total_equity": balance,
            "available_cash": available,
            "daily_pnl": daily_pnl,
            "daily_return": daily_return,
            "total_position_pct": total_position_pct,
            "total_unrealized_pnl": total_unrealized_pnl,
            "positions": positions,
        }

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        获取订单列表

        Returns:
            List[Dict]: 订单数据列表
        """
        result = []
        for order in self.orders.values():
            result.append({
                "orderid": order.orderid,
                "symbol": order.symbol,
                "direction": order.direction.value,
                "offset": order.offset.value,
                "price": order.price,
                "volume": order.volume,
                "traded": order.traded,
                "status": order.status.value,
                "time": order.time,
                "gateway_name": order.gateway_name
            })
        return result

    def get_trades(self) -> List[Dict[str, Any]]:
        """
        获取成交列表

        Returns:
            List[Dict]: 成交数据列表
        """
        result = []
        for trade in self.trades:
            result.append({
                "tradeid": trade.tradeid,
                "orderid": trade.orderid,
                "symbol": trade.symbol,
                "direction": trade.direction.value,
                "offset": trade.offset.value,
                "price": trade.price,
                "volume": trade.volume,
                "time": trade.time
            })
        return result

    def get_strategies(self) -> List[Dict[str, Any]]:
        """
        获取策略列表

        Returns:
            List[Dict]: 策略信息列表
        """
        result = []
        for name, info in self.strategies.items():
            result.append({
                "name": info.name,
                "class_name": info.class_name,
                "vt_symbol": info.vt_symbol,
                "status": info.status,
                "pos": info.pos,
                "params": info.params,
                "last_error": info.last_error
            })
        return result

    # ==================== 交易执行 ====================

    def send_order(self, vt_symbol: str, direction: str, offset: str,
                   price: float, volume: int) -> Optional[str]:
        """
        发送委托订单

        Args:
            vt_symbol: 合约代码(如 ru2505.SHFE)
            direction: 方向 LONG / SHORT
            offset: 开平 OPEN / CLOSE / CLOSETODAY / CLOSEYESTERDAY
            price: 委托价格
            volume: 委托数量

        Returns:
            str: vt_orderid,失败返回 None
        """
        if not self.main_engine:
            logger.error("Main engine not initialized, cannot send order")
            return None

        try:
            # 解析合约代码
            symbol, exchange_str = extract_vt_symbol(vt_symbol)
            exchange = Exchange(exchange_str)

            # 映射方向
            direction_map = {"LONG": Direction.LONG, "SHORT": Direction.SHORT}
            offset_map = {
                "OPEN": Offset.OPEN,
                "CLOSE": Offset.CLOSE,
                "CLOSETODAY": Offset.CLOSETODAY,
                "CLOSEYESTERDAY": Offset.CLOSEYESTERDAY
            }

            req = OrderRequest(
                symbol=symbol,
                exchange=exchange,
                direction=direction_map.get(direction, Direction.LONG),
                offset=offset_map.get(offset, Offset.OPEN),
                type=OrderType.LIMIT,
                price=price,
                volume=volume
            )

            vt_orderid = self.main_engine.send_order(req, "PaperAccount")

            if vt_orderid:
                logger.info(f"Order sent: {vt_orderid} {direction} {offset} {volume}@{price} {vt_symbol}")
                self._emit_ws("order_sent", {
                    "vt_orderid": vt_orderid,
                    "vt_symbol": vt_symbol,
                    "direction": direction,
                    "offset": offset,
                    "price": price,
                    "volume": volume
                })
            else:
                logger.warning(f"Order rejected: {direction} {offset} {volume}@{price} {vt_symbol}")

            return vt_orderid

        except Exception as e:
            logger.error(f"Send order failed: {e}")
            return None

    def cancel_order(self, vt_orderid: str) -> bool:
        """
        撤销委托订单

        Args:
            vt_orderid: 委托编号

        Returns:
            bool: 是否撤单成功
        """
        if not self.main_engine:
            logger.error("Main engine not initialized, cannot cancel order")
            return False

        try:
            order = self.orders.get(vt_orderid)
            if not order:
                logger.warning(f"Order not found: {vt_orderid}")
                return False

            req = CancelRequest(
                orderid=order.orderid,
                symbol=order.symbol,
                exchange=order.exchange
            )

            self.main_engine.cancel_order(req, order.gateway_name)

            logger.info(f"Order cancelled: {vt_orderid}")
            self._emit_ws("order_cancelled", {
                "vt_orderid": vt_orderid
            })
            return True

        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False

    # ==================== 对账映射 ====================

    def set_order_uuid_mapping(self, vt_orderid: str, order_uuid: str) -> None:
        """
        注册 vt_orderid → order_uuid 映射，供 _on_trade 回调时查找。

        由 API 层在 send_order 成功后调用，确保成交回报来临时能查到 order_uuid。
        """
        self._vt_orderid_to_order_uuid[vt_orderid] = order_uuid
        logger.debug(f"[Reconciliation] mapped vt_orderid={vt_orderid} → order_uuid={order_uuid}")

    # ==================== WebSocket客户端管理 ====================

    def register_ws_client(self, websocket):
        """
        注册WebSocket客户端连接

        Args:
            websocket: WebSocket连接对象
        """
        with self._ws_lock:
            self._ws_clients.add(websocket)
            logger.info(f"WebSocket client registered. Total: {len(self._ws_clients)}")

    def unregister_ws_client(self, websocket):
        """
        注销WebSocket客户端连接

        Args:
            websocket: WebSocket连接对象
        """
        with self._ws_lock:
            self._ws_clients.discard(websocket)
            logger.info(f"WebSocket client unregistered. Total: {len(self._ws_clients)}")

    async def _push_to_clients(self, event_type: str, data: Any):
        """
        向所有已注册的WebSocket客户端推送消息

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        disconnected = set()
        with self._ws_lock:
            for ws in self._ws_clients:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.error(f"WebSocket push error: {e}")
                    disconnected.add(ws)

        # 清理断开的连接
        for ws in disconnected:
            self.unregister_ws_client(ws)

    # ==================== 风控管理 ====================

    def get_risk_status(self) -> Dict[str, Any]:
        """
        获取风控状态

        Returns:
            Dict: 风控状态
        """
        return {
            "status": self.status.value,
            "active_rules": list(range(1, 13)),  # R1-R12
            "recent_events": [{
                "timestamp": e.timestamp,
                "rule_id": e.rule_id,
                "rule_name": e.rule_name,
                "action": e.action,
                "reason": e.reason
            } for e in self.risk_events[-10:]]  # 最近10条
        }

    def get_risk_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取风控事件历史

        Args:
            limit: 返回条数

        Returns:
            List[Dict]: 风控事件列表
        """
        events = self.risk_events[-limit:]
        return [{
            "timestamp": e.timestamp,
            "rule_id": e.rule_id,
            "rule_name": e.rule_name,
            "action": e.action,
            "symbol": e.symbol,
            "direction": e.direction,
            "reason": e.reason
        } for e in events]

    def register_risk_callback(self, callback: Callable[[RiskEvent], None]):
        """
        注册风控事件回调

        Args:
            callback: 回调函数
        """
        self.risk_callbacks.append(callback)

    def register_ws_callback(self, callback: Callable[[str, Any], None]):
        """
        注册WebSocket回调

        Args:
            callback: 回调函数(event_type, data)
        """
        self._ws_callbacks.append(callback)

    # ==================== CTP连接 ====================

    def connect_ctp(self, setting: Dict[str, str]) -> bool:
        """
        连接CTP

        Args:
            setting: CTP连接配置
                {
                    "用户名": "",
                    "密码": "",
                    "经纪商代码": "9999",
                    "交易服务器": "",
                    "行情服务器": "",
                    "产品名称": "simnow_client_test",
                    "授权编码": ""
                }

        Returns:
            bool: 是否连接成功
        """
        if not self.main_engine:
            logger.error("Main engine not initialized")
            return False

        try:
            self.main_engine.connect(setting, "CTP")
            logger.info("CTP connection initiated")
            return True
        except Exception as e:
            logger.error(f"CTP connection failed: {e}")
            return False

    def disconnect_ctp(self):
        """断开CTP连接"""
        if self.main_engine:
            self.main_engine.close()
            logger.info("CTP disconnected")

    # ==================== 工具方法 ====================

    def is_trading_hours(self) -> bool:
        """
        检查是否在交易时间

        Returns:
            bool: 是否在交易时间
        """
        now = datetime.now().time()

        # 日盘: 09:00-10:15, 10:30-11:30, 13:30-15:00
        # 夜盘: 21:00-23:00 (部分品种到01:00/02:30)

        morning1 = (time(9, 0), time(10, 15))
        morning2 = (time(10, 30), time(11, 30))
        afternoon = (time(13, 30), time(15, 0))
        night = (time(21, 0), time(23, 0))

        return (
            morning1[0] <= now <= morning1[1] or
            morning2[0] <= now <= morning2[1] or
            afternoon[0] <= now <= afternoon[1] or
            night[0] <= now <= night[1]
        )

    def get_status(self) -> Dict[str, Any]:
        """
        获取桥接状态

        Returns:
            Dict: 状态信息
        """
        return {
            "status": self.status.value,
            "is_running": self.status == BridgeStatus.RUNNING,
            "is_trading_hours": self.is_trading_hours(),
            "strategies_count": len(self.strategies),
            "positions_count": len(self.positions),
            "orders_count": len(self.orders),
            "trades_count": len(self.trades),
            "risk_events_count": len(self.risk_events)
        }



# Paper Trading Bridge - 用于开发和测试
class PaperBridge:
    """简化版的 Paper Trading 桥接"""
    def __init__(self):
        self.status = BridgeStatus.RUNNING
        self._event_loop = None
        self._orders = {}
        self._positions = {}  # {symbol: {direction: {volume, price, pnl}}}
        self._account = {"balance": 1000000.0, "available": 1000000.0}
        self._starting_balance = 1000000.0  # 日初权益(用于计算 daily_pnl)
        self._ws_clients = []
        self._last_price = {}
        # 加载统一风控规则(Layer + Severity 从 YAML 读取)
        self._rules = self._load_risk_rules()

    def _load_risk_rules(self):
        """从 risk/rules/risk_rules.yaml 加载规则定义"""
        try:
            import yaml
            from pathlib import Path
            rules_path = Path(__file__).parent.parent / "risk" / "rules" / "risk_rules.yaml"
            with open(rules_path, encoding="utf-8") as f:
                return yaml.safe_load(f).get("rules", [])
        except Exception:
            return []

    # YAML 短 ID → 前端 RiskRuleId 长名映射(与 routes/risk.py RULE_ID_MAP 对齐)
    _SHORT_TO_LONG = {
        'R1': 'R1_SINGLE_SYMBOL',
        'R2': 'R2_DAILY_LOSS',
        'R3': 'R3_PRICE_LIMIT',
        'R4': 'R4_TOTAL_MARGIN',
        'R5': 'R5_VOLATILITY',
        'R6': 'R6_LIQUIDITY',
        'R7': 'R7_CONSECUTIVE_LOSS',
        'R8': 'R8_TRADING_HOURS',
        'R9': 'R9_CAPITAL_SUFFICIENCY',
        'R10': 'R10_MACRO_CIRCUIT_BREAKER',
        'R11': 'R11_DISPOSITION_EFFECT',
        'R12': 'R12_CANCEL_LIMIT',
    }

    def get_risk_rules(self):
        """
        获取风控规则配置(前端 /api/risk/rules 使用)
        layer 返回 numeric (1/2/3),severity 返回 PASS/WARN/BLOCK
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        LAYER_TO_SEVERITY = {1: "PASS", 2: "WARN", 3: "BLOCK"}
        result = []
        for r in self._rules:
            rule_id = r.get("id", "")
            layer = r.get("layer", 2)
            severity = LAYER_TO_SEVERITY.get(layer, "WARN")
            result.append({
                "id": rule_id,
                "ruleId": self._SHORT_TO_LONG.get(rule_id, rule_id),
                "name": r.get("name", ""),
                "layer": layer,
                "threshold": r.get("threshold", 0),
                "severity": severity,
                "currentValue": 0,
                "unit": "ratio",
                "enabled": r.get("enabled", True),
                "updatedAt": now,
            })
        return result

    def get_portfolio(self):
        """
        返回聚合的组合数据(用于前端 PortfolioData)
        包含账户统计 + 持仓列表
        """
        positions = self.get_positions()
        balance = self._account.get("balance", 1000000.0)
        available = self._account.get("available", balance)
        starting = getattr(self, "_starting_balance", 1000000.0)

        # 计算浮动盈亏合计
        total_unrealized_pnl = sum(p.get("pnl", 0) for p in positions)
        daily_pnl = balance - starting
        daily_return = (daily_pnl / starting) if starting > 0 else 0.0

        # 持仓保证金估算(简化:持仓价值 * 10% 保证金率)
        total_position_value = sum(
            p.get("price", 0) * p.get("volume", 0) * 10 for p in positions
        )
        total_position_pct = (total_position_value / balance) if balance > 0 else 0.0

        return {
            "date": self._account.get("date", ""),
            "total_equity": balance,
            "available_cash": available,
            "daily_pnl": daily_pnl,
            "daily_return": daily_return,
            "total_position_pct": total_position_pct,
            "total_unrealized_pnl": total_unrealized_pnl,
            "positions": positions,
        }  # 记录每个品种的最新价格

    def send_order(self, vt_symbol, direction, offset, price, volume, order_type="LIMIT"):
        import uuid
        vt_orderid = f"{vt_symbol}-{direction}-{uuid.uuid4().hex[:8]}"
        self._orders[vt_orderid] = {
            "status": "filled",
            "filled_price": price,
            "vt_symbol": vt_symbol,
            "direction": direction,
            "offset": offset,
            "volume": volume
        }
        # 更新持仓
        symbol = vt_symbol.split(".")[0]
        key = f"{symbol}.{direction}"
        if key not in self._positions:
            self._positions[key] = {"symbol": symbol, "direction": direction, "volume": 0, "price": price, "pnl": 0}
        pos = self._positions[key]
        if offset == "OPEN":
            pos["volume"] += volume
            pos["price"] = price
        elif offset == "CLOSE" and pos["volume"] >= volume:
            pos["volume"] -= volume
        self._last_price[symbol] = price
        return vt_orderid

    def cancel_order(self, vt_orderid):
        return vt_orderid in self._orders

    def get_positions(self):
        """返回当前持仓列表"""
        result = []
        for pos in self._positions.values():
            if pos["volume"] > 0:
                symbol = pos["symbol"]
                current_price = self._last_price.get(symbol, pos["price"])
                # 简化盈亏计算
                pnl = (current_price - pos["price"]) * pos["volume"] * 10
                pos["pnl"] = pnl
                result.append(pos.copy())
        return result

    def get_account(self):
        return self._account

    def get_orders(self):
        return list(self._orders.values())

    def get_trades(self):
        """返回成交记录(基于已成交订单)"""
        result = []
        for order_id, order in self._orders.items():
            if order.get("status") == "filled":
                result.append({
                    "tradeid": order_id,
                    "orderid": order_id,
                    "symbol": order.get("vt_symbol", "").split(".")[0] if order.get("vt_symbol") else "",
                    "direction": order.get("direction", ""),
                    "offset": order.get("offset", ""),
                    "price": order.get("filled_price", 0),
                    "volume": order.get("volume", 0),
                    "time": ""
                })
        return result

    def get_status(self):
        return {"status": "running", "connected": True, "mode": "paper"}

    def get_risk_status(self):
        """
        获取风控状态(前端 /api/risk/status 使用)
        返回格式与 RiskRuleItem Pydantic 模型一致
        """
        from datetime import datetime

        # 定义12条风控规则状态
        rules = [
            {"ruleId": "R1_SINGLE_SYMBOL", "ruleName": "R1 单品种持仓限制(动态)", "layer": 3, "severity": "PASS", "currentValue": 0.18, "threshold": 0.30, "message": ""},
            {"ruleId": "R2_DAILY_LOSS", "ruleName": "R2 单日最大亏损限制", "layer": 2, "severity": "PASS", "currentValue": 0.02, "threshold": 0.05, "message": ""},
            {"ruleId": "R3_PRICE_LIMIT", "ruleName": "R3 涨跌停限制", "layer": 1, "severity": "PASS", "currentValue": 0.0, "threshold": 0.0, "message": "未触及涨跌停"},
            {"ruleId": "R4_TOTAL_MARGIN", "ruleName": "R4 总保证金上限(分时段)", "layer": 3, "severity": "PASS", "currentValue": 0.45, "threshold": 0.70, "message": ""},
            {"ruleId": "R5_VOLATILITY", "ruleName": "R5 波动率异常过滤", "layer": 1, "severity": "PASS", "currentValue": 0.03, "threshold": 0.05, "message": ""},
            {"ruleId": "R6_LIQUIDITY", "ruleName": "R6 流动性检查", "layer": 1, "severity": "PASS", "currentValue": 5000, "threshold": 1000, "message": ""},
            {"ruleId": "R7_CONSECUTIVE_LOSS", "ruleName": "R7 连续亏损暂停", "layer": 2, "severity": "PASS", "currentValue": 0, "threshold": 5, "message": "无连续亏损"},
            {"ruleId": "R8_TRADING_HOURS", "ruleName": "R8 交易时间检查", "layer": 1, "severity": "PASS", "currentValue": 1.0, "threshold": 0.0, "message": "交易时段正常"},
            {"ruleId": "R9_CAPITAL_SUFFICIENCY", "ruleName": "R9 资金充足性检查", "layer": 3, "severity": "PASS", "currentValue": 0.95, "threshold": 0.05, "message": "资金充足"},
            {"ruleId": "R10_MACRO_CIRCUIT_BREAKER", "ruleName": "R10 宏观熔断", "layer": 1, "severity": "PASS", "currentValue": 0.45, "threshold": -0.5, "message": "宏观打分正常"},
            {"ruleId": "R11_DISPOSITION_EFFECT", "ruleName": "R11 处置效应监控", "layer": 2, "severity": "PASS", "currentValue": 48, "threshold": 24, "message": ""},
            {"ruleId": "R12_CANCEL_LIMIT", "ruleName": "R12 撤单次数限制", "layer": 2, "severity": "PASS", "currentValue": 0, "threshold": 10, "message": ""},
        ]

        now = datetime.now().isoformat()
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "overallStatus": "PASS",
            "rules": [
                {**r, "triggered": r["severity"] != "PASS", "updatedAt": now}
                for r in rules
            ],
            "triggeredCount": 0,
            "circuitBreaker": False,
            "updatedAt": now,
        }

    def update_risk_rule(self, rule_data: dict):
        """
        更新风控规则配置
        前端调用链:PUT /api/risk/rules/{ruleId} → routes/risk.py → bridge.update_risk_rule()
        rule_data 包含:ruleId, threshold, enabled, params 等字段
        """
        import logging
        logger = logging.getLogger("PaperBridge")
        rule_id = rule_data.get("ruleId", "")
        logger.info(f"[PaperBridge] update_risk_rule: {rule_id} → {rule_data}")

        # 更新内存中的规则配置
        for rule in self._rules:
            short_id = rule_id.split("_")[0] if "_" in rule_id else rule_id
            if rule.get("id") == short_id or rule.get("id") == rule_id:
                if "threshold" in rule_data:
                    rule["threshold"] = rule_data["threshold"]
                if "enabled" in rule_data:
                    rule["enabled"] = rule_data["enabled"]
                logger.info(f"[PaperBridge] 规则 {rule_id} 已更新: threshold={rule.get('threshold')}, enabled={rule.get('enabled')}")
                break
        else:
            logger.warning(f"[PaperBridge] update_risk_rule: 规则 {rule_id} 未找到")

    def get_risk_status(self):
        """
        获取风控状态
        返回格式与 RiskRuleItem Pydantic 模型一致
        """
        from datetime import datetime

        # 定义11条风控规则状态
        rules = [
            {"ruleId": "R1_SINGLE_SYMBOL", "ruleName": "R1 单品种持仓限制(动态)", "layer": 3, "severity": "PASS", "currentValue": 0.18, "threshold": 0.30, "message": ""},
            {"ruleId": "R2_DAILY_LOSS", "ruleName": "R2 单日最大亏损限制", "layer": 2, "severity": "PASS", "currentValue": 0.02, "threshold": 0.05, "message": ""},
            {"ruleId": "R3_PRICE_LIMIT", "ruleName": "R3 涨跌停限制", "layer": 1, "severity": "PASS", "currentValue": 0.0, "threshold": 0.0, "message": "未触及涨跌停"},
            {"ruleId": "R4_TOTAL_MARGIN", "ruleName": "R4 总保证金上限(分时段)", "layer": 3, "severity": "PASS", "currentValue": 0.45, "threshold": 0.70, "message": ""},
            {"ruleId": "R5_VOLATILITY", "ruleName": "R5 波动率异常过滤", "layer": 1, "severity": "PASS", "currentValue": 0.03, "threshold": 0.05, "message": ""},
            {"ruleId": "R6_LIQUIDITY", "ruleName": "R6 流动性检查", "layer": 1, "severity": "PASS", "currentValue": 5000, "threshold": 1000, "message": ""},
            {"ruleId": "R7_CONSECUTIVE_LOSS", "ruleName": "R7 连续亏损暂停", "layer": 2, "severity": "PASS", "currentValue": 0, "threshold": 5, "message": "无连续亏损"},
            {"ruleId": "R8_TRADING_HOURS", "ruleName": "R8 交易时间检查", "layer": 1, "severity": "PASS", "currentValue": 1.0, "threshold": 0.0, "message": "交易时段正常"},
            {"ruleId": "R9_CAPITAL_SUFFICIENCY", "ruleName": "R9 资金充足性检查", "layer": 3, "severity": "PASS", "currentValue": 0.95, "threshold": 0.05, "message": "资金充足"},
            {"ruleId": "R10_MACRO_CIRCUIT_BREAKER", "ruleName": "R10 宏观熔断", "layer": 1, "severity": "PASS", "currentValue": 0.45, "threshold": -0.5, "message": "宏观打分正常"},
            {"ruleId": "R11_DISPOSITION_EFFECT", "ruleName": "R11 处置效应监控", "layer": 2, "severity": "PASS", "currentValue": 48, "threshold": 24, "message": ""},
            {"ruleId": "R12_CANCEL_LIMIT", "ruleName": "R12 撤单次数限制", "layer": 2, "severity": "PASS", "currentValue": 0, "threshold": 10, "message": ""},
        ]

        now = datetime.now().isoformat()
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "overallStatus": "PASS",
            "rules": [
                {**r, "triggered": r["severity"] != "PASS", "updatedAt": now}
                for r in rules
            ],
            "triggeredCount": 0,
            "circuitBreaker": False,
            "updatedAt": now,
        }



    def is_trading_hours(self):
        return True

    def register_ws_client(self, ws):
        pass

    def unregister_ws_client(self, ws):
        pass

    def register_ws_callback(self, callback):
        """注册 WebSocket 回调(vnpy_ws.py 使用)"""
        pass

    def unregister_ws_callback(self, callback):
        pass

    def register_risk_callback(self, callback):
        """注册风控回调"""
        pass

    def unregister_risk_callback(self, callback):
        pass



    def get_cancel_count(self, minutes: int = 60) -> int:
        """
        获取撤单次数(Paper 模式下返回 0,因为 Paper 订单直接成交无撤单)
        提供此方法避免 risk.py R12 回退时 AttributeError
        """
        return 0


# ---------------------------------------------------------------------------
# 模块级注入:run.py 启动后将真实 VNpyBridge 注入此处
# ---------------------------------------------------------------------------
_injected_vnpy_bridge = None


def set_vnpy_bridge(bridge):
    """由 run.py 调用,注入真实 VNpyBridge 实例"""
    global _injected_vnpy_bridge
    _injected_vnpy_bridge = bridge


class _BridgeProxy:
    """
    懒代理桥接器。
    在 __getattr__ 时调用 macro_api_server.get_vnpy_bridge(),
    保证 routes/trading.py 和 routes/risk.py 与 macro_api_server 共用同一实例。
    """
    __slots__ = ('_bridge',)

    def __init__(self):
        object.__setattr__(self, '_bridge', None)

    def _resolve(self):
        b = object.__getattribute__(self, '_bridge')
        if b is not None:
            return b
        # 优先使用模块级注入的真实 VNpyBridge
        if _injected_vnpy_bridge is not None:
            b = _injected_vnpy_bridge
        else:
            # Fallback: PaperBridge(仅在 run.py 未注入时使用)
            try:
                b = PaperBridge()
            except Exception:
                b = None
        if b is not None:
            object.__setattr__(self, '_bridge', b)
        return b

    def __getattr__(self, name):
        b = self._resolve()
        if b is None:
            raise AttributeError(f"'NoneType' object has no attribute '{name}' - VNpyBridge not initialised")
        return getattr(b, name)

    def __setattr__(self, name, value):
        if name == '_bridge' or name == '_resolve':
            object.__setattr__(self, name, value)
        else:
            b = self._resolve()
            if b is None:
                raise AttributeError(f"'NoneType' object has no attribute '{name}' - VNpyBridge not initialised")
            setattr(b, name, value)

    def __dir__(self):
        try:
            b = self._resolve()
            if b:
                return dir(b)
        except Exception:
            pass
        return []

    @property
    def status(self):
        b = self._resolve()
        if b is None:
            from .vnpy_bridge import BridgeStatus
            return BridgeStatus.STOPPED
        return b.status


# 全局桥接实例 - 懒代理(保留向后兼容,新代码请用 get_vnpy_bridge())
bridge = _BridgeProxy()


def get_vnpy_bridge():
    """获取全局 VNpyBridge 实例(线程安全懒加载)"""
    if _injected_vnpy_bridge is not None:
        return _injected_vnpy_bridge
    return bridge


if __name__ == "__main__":
    # 测试代码
    print("VNpyBridge test")

    # 启动
    if bridge.start():
        print("✓ VNpy started")

        # 查看状态
        status = bridge.get_status()
        print(f"Status: {status}")

        # 停止
        bridge.stop()
        print("✓ VNpy stopped")
    else:
        print("✗ Failed to start VNpy")
