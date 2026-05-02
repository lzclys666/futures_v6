# -*- coding: utf-8 -*-
"""
MacroRiskApp - 风控引擎 (基于 core/risk/risk_engine.py 前 5 条核心规则)

R10 - 宏观熔断: 宏观评分 < 30 禁做多, > 70 禁做空
R5  - 波动率异常过滤: ATR/价格超阈值 → WARN/BLOCK
R6  - 流动性检查: 订单量 vs 均量 + 盘口深度
R8  - 交易时间检查: 非交易时段禁下单, 集合竞价禁开仓
R3  - 涨跌停限制: 触及涨跌停禁开仓
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, time
from enum import Enum
import logging

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.object import OrderData, TradeData, PositionData, AccountData
from vnpy.trader.constant import Direction, Offset, Status, Product


logger = logging.getLogger("MacroRiskApp")


# ============================================================================
# 魔法数字常量
# ============================================================================
# 涨跌停/最小价格精度
_MIN_VALID_PRICE = 0.01

# 夜盘结束时间（小时）
_NIGHT_SESSION_END_HOUR = 23

# 宏观熔断阈值（归一化评分 0~100）
_MACRO_FUSE_LOW = 30.0
_MACRO_FUSE_HIGH = 70.0
_MACRO_HYSTERESIS = 5.0

# 波动率阈值（归一化 0~1）
_VOL_WARN_RATIO = 0.25   # 25%+ 预警
_VOL_BLOCK_RATIO = 0.35  # 35%+ 阻止

# 流动性阈值
_VOL_RATIO_LIMIT = 0.05
_DEPTH_RATIO_LIMIT = 0.30

# 大单确认阈值（手）
_LARGE_ORDER_THRESHOLD = 100

# composite_score → macro_score 映射：(score -1~1) → 0~100
_SCORE_MIDPOINT = 50.0
_SCORE_SCALE = 50.0


class RiskAction(Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


class RiskEngine(BaseEngine):
    """
    风控引擎

    监听 eOrder 事件，按优先级顺序执行规则链拦截风险订单
    """

    name = "RiskEngine"

    # 规则执行顺序: R8(时间) → R10(熔断) → R3(涨跌停) → R5(波动率) → R6(流动性)
    RULE_ORDER = ["R8", "R10", "R3", "R5", "R6"]

    # 交易时段 (商品期货标准时段)
    TRADING_SESSIONS = [
        (time(9, 0), time(10, 15)),
        (time(10, 30), time(11, 30)),
        (time(13, 30), time(15, 0)),
    ]
    AUCTION_SESSIONS = [
        (time(8, 55), time(9, 0)),
        (time(20, 55), time(21, 0)),
    ]

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__(main_engine, event_engine, "RiskEngine")

        # === 可配置参数 ===
        # R10: 宏观熔断
        self.macro_fuse_low = _MACRO_FUSE_LOW
        self.macro_fuse_high = _MACRO_FUSE_HIGH
        self.macro_hysteresis = _MACRO_HYSTERESIS

        # R5: 波动率过滤
        self.vol_warn_multiplier = _VOL_WARN_RATIO
        self.vol_block_multiplier = _VOL_BLOCK_RATIO

        # R6: 流动性检查
        self.vol_ratio_limit = _VOL_RATIO_LIMIT
        self.depth_ratio_limit = _DEPTH_RATIO_LIMIT

        # R8: 交易时间
        self.enable_night_session = True

        # 状态追踪
        self.rules_enabled: Dict[str, bool] = {
            "R8": True, "R10": True, "R3": True, "R5": True, "R6": True
        }
        self.violation_count: Dict[str, int] = {k: 0 for k in self.RULE_ORDER}
        self.last_macro_score: Optional[float] = None
        self.last_trigger_score: Optional[float] = None

        # 注册事件
        self.event_engine.register("eOrder", self._on_order)

        logger.info(f"RiskEngine 已启动, {len(self.RULE_ORDER)} 条核心规则就绪")

    # ==================== 事件处理 ====================

    def _on_order(self, event: Event) -> None:
        """订单事件入口: 拦截前检查"""
        order: OrderData = event.data
        if order.status != Status.SUBMITTING:
            return

        violations = self._check_rules(order)
        if violations:
            blocked = any(v["action"] == "BLOCK" for v in violations)
            event_data = {
                "vt_orderid": order.vt_orderid,
                "symbol": order.symbol,
                "direction": order.direction.value,
                "offset": order.offset.value,
                "price": order.price,
                "volume": order.volume,
                "violations": violations,
                "blocked": blocked,
            }
            risk_event = Event(type="eRiskRule", data=event_data)
            self.event_engine.put(risk_event)

            for v in violations:
                logger.warning(f"[{v['rule']}] {v['action']}: {v['reason']}")

    # ==================== 规则检查 ====================

    def _check_rules(self, order: OrderData) -> List[dict]:
        """按优先级检查所有启用的规则, 返回违规列表"""
        violations = []

        checks = {
            "R8": self._check_r8,
            "R10": self._check_r10,
            "R3": self._check_r3,
            "R5": self._check_r5,
            "R6": self._check_r6,
        }

        for rule_id in self.RULE_ORDER:
            if not self.rules_enabled.get(rule_id, True):
                continue
            result = checks[rule_id](order)
            if result:
                violations.append(result)
                if result["action"] == "BLOCK":
                    break

        return violations

    # ---------- R8: 交易时间检查 ----------

    def _check_r8(self, order: OrderData) -> Optional[dict]:
        now = datetime.now().time()

        # 检查集合竞价
        for start, end in self.AUCTION_SESSIONS:
            if start <= now <= end:
                if order.offset == Offset.OPEN:
                    return {
                        "rule": "R8", "action": "BLOCK",
                        "reason": f"集合竞价期间禁止开仓 ({now.strftime('%H:%M')})"
                    }
                return None  # 平仓允许

        # 检查常规交易时段
        sessions = list(self.TRADING_SESSIONS)
        if self.enable_night_session:
            sessions.append((time(21, 0), time(_NIGHT_SESSION_END_HOUR, 0)))

        in_trading = any(start <= now <= end for start, end in sessions)
        if not in_trading:
            return {
                "rule": "R8", "action": "BLOCK",
                "reason": f"非交易时段 ({now.strftime('%H:%M')})"
            }

        return None

    # ---------- R10: 宏观熔断 ----------

    def _check_r10(self, order: OrderData) -> Optional[dict]:
        # 获取宏观评分 (从 main_engine 的 signal_bridge)
        signal_bridge = getattr(self.main_engine, 'signal_bridge', None)
        macro_score = 50.0
        if signal_bridge:
            symbol_base = ''.join(c for c in order.symbol if not c.isdigit()).upper()
            score = signal_bridge.get_latest_score(symbol_base)
            if score is not None:
                # score 是 -1~1 归一化值, 映射到 0~100
                macro_score = _SCORE_MIDPOINT + score * _SCORE_SCALE

        # 滞后恢复检查
        if self.last_trigger_score is not None:
            if self.last_trigger_score <= self.macro_fuse_low:
                if macro_score <= self.macro_fuse_low + self.macro_hysteresis:
                    return {
                        "rule": "R10", "action": "BLOCK",
                        "reason": f"宏观熔断中(看空): 评分{macro_score:.0f}, 需回升至{self.macro_fuse_low + self.macro_hysteresis:.0f}"
                    }
            elif self.last_trigger_score >= self.macro_fuse_high:
                if macro_score >= self.macro_fuse_high - self.macro_hysteresis:
                    return {
                        "rule": "R10", "action": "BLOCK",
                        "reason": f"宏观熔断中(看多): 评分{macro_score:.0f}, 需回落至{self.macro_fuse_high - self.macro_hysteresis:.0f}"
                    }
            self.last_trigger_score = None

        # 检查是否触发熔断
        if macro_score <= self.macro_fuse_low and order.direction == Direction.LONG:
            self.last_trigger_score = macro_score
            return {
                "rule": "R10", "action": "BLOCK",
                "reason": f"宏观熔断触发: 评分{macro_score:.0f} <= {self.macro_fuse_low}, 禁止做多"
            }
        if macro_score >= self.macro_fuse_high and order.direction == Direction.SHORT:
            self.last_trigger_score = macro_score
            return {
                "rule": "R10", "action": "BLOCK",
                "reason": f"宏观熔断触发: 评分{macro_score:.0f} >= {self.macro_fuse_high}, 禁止做空"
            }

        return None

    # ---------- R3: 涨跌停限制 ----------

    def _check_r3(self, order: OrderData) -> Optional[dict]:
        if order.price <= 0:
            return {
                "rule": "R3", "action": "BLOCK",
                "reason": "委托价格必须大于 0"
            }

        # 尝试从行情数据获取涨跌停价格
        symbol = order.vt_symbol if hasattr(order, 'vt_symbol') else order.symbol
        try:
            tick = self.main_engine.get_tick(symbol)
            if tick:
                if order.direction == Direction.LONG and order.offset == Offset.OPEN:
                    if tick.ask_price_1 <= 0 or tick.ask_price_1 <= _MIN_VALID_PRICE:
                        return {
                            "rule": "R3", "action": "BLOCK",
                            "reason": "无有效卖一价, 可能涨停"
                        }
                elif order.direction == Direction.SHORT and order.offset == Offset.OPEN:
                    if tick.bid_price_1 <= 0 or tick.bid_price_1 <= _MIN_VALID_PRICE:
                        return {
                            "rule": "R3", "action": "BLOCK",
                            "reason": "无有效买一价, 可能跌停"
                        }
        except Exception:
            pass

        return None

    # ---------- R5: 波动率异常过滤 ----------

    def _check_r5(self, order: OrderData) -> Optional[dict]:
        # 从 SignalBridge 获取波动率数据 (简化实现)
        signal_bridge = getattr(self.main_engine, 'signal_bridge', None)
        if not signal_bridge:
            return None

        symbol_base = ''.join(c for c in order.symbol if not c.isdigit()).upper()
        volatility = signal_bridge.get_latest_score(f"{symbol_base}_volatility")

        if volatility is None:
            return None

        # 波动率已归一化到 0~1, 检查阈值
        vol_ratio = abs(volatility)

        if vol_ratio > _VOL_BLOCK_RATIO:  # 35%+ 波动率
            return {
                "rule": "R5", "action": "BLOCK",
                "reason": f"波动率异常: {vol_ratio*100:.1f}% 超过限制"
            }
        if vol_ratio > _VOL_WARN_RATIO:  # 25%+ 预警
            return {
                "rule": "R5", "action": "WARN",
                "reason": f"波动率偏高: {vol_ratio*100:.1f}%"
            }

        return None

    # ---------- R6: 流动性检查 ----------

    def _check_r6(self, order: OrderData) -> Optional[dict]:
        # 简化实现: 检查订单量是否合理
        if order.volume <= 0:
            return {
                "rule": "R6", "action": "BLOCK",
                "reason": "订单量必须大于 0"
            }

        # 大单检查 (>LARGE_ORDER_THRESHOLD手需确认)
        if order.volume > _LARGE_ORDER_THRESHOLD:
            return {
                "rule": "R6", "action": "WARN",
                "reason": f"大单预警: {order.volume} 手 > {_LARGE_ORDER_THRESHOLD} 手, 建议拆单"
            }

        return None

    # ==================== 管理接口 ====================

    def get_rule_status(self) -> List[dict]:
        """获取规则状态"""
        return [
            {
                "rule_id": rid,
                "enabled": self.rules_enabled.get(rid, True),
                "violations": self.violation_count.get(rid, 0),
            }
            for rid in self.RULE_ORDER
        ]

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        """启用/禁用规则"""
        if rule_id in self.rules_enabled:
            self.rules_enabled[rule_id] = enabled
            logger.info(f"规则 {rule_id}: {'启用' if enabled else '禁用'}")
            return True
        return False

    def set_macro_score(self, score: float):
        """设置当前宏观评分 (供 SignalBridge 回调)"""
        self.last_macro_score = score
