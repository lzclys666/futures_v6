#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Risk Engine Core - 风控引擎核心
基于 V6.1 风控规则手册科学修订版

三层防御架构：
- Layer 1: 市场系统性风险防御（R10, R5, R6, R8, R3）
- Layer 2: 账户级风险防御（R2, R7, R11, R12）
- Layer 3: 交易执行风险防御（R1, R4, R9）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Any
import numpy as np
import yaml
import json
import time as time_mod
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# 统一风控模型
# Layer: 1 (PASS) / 2 (WARN) / 3 (BLOCK)  — numeric
# Severity: PASS / WARN / BLOCK           — 统一字符串
# =============================================================================
LAYER_TO_SEVERITY = {1: "PASS", 2: "WARN", 3: "BLOCK"}


class RiskAction(Enum):
    """风控动作"""
    PASS = "PASS"      # 通过
    WARN = "WARN"      # 警告（记录但允许）
    BLOCK = "BLOCK"    # 拦截（禁止下单）


@dataclass
class RiskResult:
    """风控检查结果"""
    rule_id: str
    action: RiskAction
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskContext:
    """风控上下文"""
    account: Optional[Any] = None          # 账户信息
    positions: Dict[str, Any] = field(default_factory=dict)  # 持仓
    market_data: Dict[str, Any] = field(default_factory=dict)  # 行情数据
    order_history: List[Any] = field(default_factory=list)  # 订单历史
    warnings: List[RiskResult] = field(default_factory=list)  # 警告记录
    
    def add_warning(self, result: RiskResult):
        self.warnings.append(result)


@dataclass
class OrderRequest:
    """订单请求（简化版）"""
    symbol: str
    exchange: str
    direction: str  # LONG / SHORT
    offset: str     # OPEN / CLOSE
    price: float
    volume: int
    order_type: str = "LIMIT"


class RiskRule(ABC):
    """风控规则抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        # 从类名提取规则ID: R10_MacroFuseRule -> R10
        class_name = self.__class__.__name__
        if '_' in class_name and class_name[0] == 'R':
            self.rule_id = class_name.split('_')[0]
        else:
            self.rule_id = class_name.replace('Rule', '').replace('Risk', 'R')
        
    def is_enabled(self) -> bool:
        return self.enabled
    
    @abstractmethod
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        """检查订单"""
        pass
    
    def _create_result(self, action: RiskAction, message: str, **details) -> RiskResult:
        return RiskResult(
            rule_id=self.rule_id,
            action=action,
            message=message,
            details=details
        )


# ==================== Layer 1: 市场系统性风险 ====================

class R10_MacroFuseRule(RiskRule):
    """
    R10: 宏观熔断
    宏观评分 < 30分：禁止做多
    宏观评分 > 70分：禁止做空
    滞后区间：5分（防止临界点频繁触发）
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fuse_low = config.get('fuse_low', 30)
        self.fuse_high = config.get('fuse_high', 70)
        self.hysteresis = config.get('hysteresis', 5)
        self.last_trigger_score = None
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        # 获取宏观评分（从上下文或外部服务）
        macro_score = context.market_data.get('macro_score', 50)
        symbol = order.symbol
        
        # 检查是否需要恢复（滞后区间）
        if self.last_trigger_score is not None:
            if self.last_trigger_score <= self.fuse_low:
                # 上次因极端看空触发，需回升至 30+5=35 才恢复
                if macro_score <= self.fuse_low + self.hysteresis:
                    return self._create_result(
                        RiskAction.BLOCK,
                        f"宏观熔断中（看空）：评分{macro_score}，需回升至{self.fuse_low + self.hysteresis}才恢复",
                        macro_score=macro_score,
                        threshold=self.fuse_low + self.hysteresis
                    )
            elif self.last_trigger_score >= self.fuse_high:
                # 上次因极端看多触发，需回落至 70-5=65 才恢复
                if macro_score >= self.fuse_high - self.hysteresis:
                    return self._create_result(
                        RiskAction.BLOCK,
                        f"宏观熔断中（看多）：评分{macro_score}，需回落至{self.fuse_high - self.hysteresis}才恢复",
                        macro_score=macro_score,
                        threshold=self.fuse_high - self.hysteresis
                    )
            # 已恢复
            self.last_trigger_score = None
        
        # 检查是否触发熔断
        if macro_score <= self.fuse_low:
            if order.direction == "LONG":
                self.last_trigger_score = macro_score
                return self._create_result(
                    RiskAction.BLOCK,
                    f"宏观熔断触发：评分{macro_score} <= {self.fuse_low}，禁止做多",
                    macro_score=macro_score,
                    threshold=self.fuse_low
                )
                
        if macro_score >= self.fuse_high:
            if order.direction == "SHORT":
                self.last_trigger_score = macro_score
                return self._create_result(
                    RiskAction.BLOCK,
                    f"宏观熔断触发：评分{macro_score} >= {self.fuse_high}，禁止做空",
                    macro_score=macro_score,
                    threshold=self.fuse_high
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"宏观评分{macro_score}，未触发熔断",
            macro_score=macro_score
        )


class R5_VolatilityFilterRule(RiskRule):
    """
    R5: 波动率异常过滤（个人交易者简化版）
    ATR(14)/价格 > 2倍近期均值 → WARN
    ATR(14)/价格 > 3倍近期均值 → BLOCK
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.warn_multiplier = config.get('warn_multiplier', 2.0)
        self.block_multiplier = config.get('block_multiplier', 3.0)
        self.lookback_days = config.get('lookback_days', 20)
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        symbol = order.symbol
        
        # 获取ATR数据和价格
        atr_14 = context.market_data.get(f'{symbol}_atr_14', 0)
        current_price = context.market_data.get(f'{symbol}_price', order.price)
        atr_history = context.market_data.get(f'{symbol}_atr_history', [])
        
        if not atr_14 or not current_price:
            return self._create_result(
                RiskAction.PASS,
                "无ATR数据，跳过检查",
                symbol=symbol
            )
        
        # 计算ATR/价格比例
        atr_ratio = atr_14 / current_price
        
        # 计算近期均值
        if len(atr_history) >= self.lookback_days:
            recent_atr = atr_history[-self.lookback_days:]
            atr_mean = np.mean([a / current_price for a in recent_atr])
        else:
            # 数据不足，使用默认阈值
            atr_mean = 0.02  # 默认2%
        
        # 检查是否超过阈值
        if atr_ratio > atr_mean * self.block_multiplier:
            return self._create_result(
                RiskAction.BLOCK,
                f"波动率异常：ATR/价格={atr_ratio*100:.2f}%，超过近期均值{atr_mean*100:.2f}%的{self.block_multiplier}倍",
                atr_ratio=atr_ratio,
                atr_mean=atr_mean,
                threshold=atr_mean * self.block_multiplier
            )
        
        if atr_ratio > atr_mean * self.warn_multiplier:
            return self._create_result(
                RiskAction.WARN,
                f"波动率偏高：ATR/价格={atr_ratio*100:.2f}%，超过近期均值{atr_mean*100:.2f}%的{self.warn_multiplier}倍",
                atr_ratio=atr_ratio,
                atr_mean=atr_mean,
                threshold=atr_mean * self.warn_multiplier
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"波动率正常：ATR/价格={atr_ratio*100:.2f}%",
            atr_ratio=atr_ratio
        )


class R6_LiquidityCheckRule(RiskRule):
    """
    R6: 流动性检查
    订单量 / 20日日均成交量 < 5%
    订单量 < 盘口深度 * 30%
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.volume_ratio_limit = config.get('volume_ratio_limit', 0.05)
        self.depth_ratio_limit = config.get('depth_ratio_limit', 0.30)
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        symbol = order.symbol
        order_volume = order.volume
        
        # 获取20日日均成交量
        avg_volume_20d = context.market_data.get(f'{symbol}_avg_volume_20d', 0)
        
        if avg_volume_20d > 0:
            volume_ratio = order_volume / avg_volume_20d
            if volume_ratio > self.volume_ratio_limit:
                return self._create_result(
                    RiskAction.BLOCK,
                    f"流动性不足：订单量{order_volume}超过20日均量{avg_volume_20d:.0f}的{self.volume_ratio_limit*100:.0f}%",
                    order_volume=order_volume,
                    avg_volume=avg_volume_20d,
                    ratio=volume_ratio
                )
        
        # 检查盘口深度
        orderbook_depth = context.market_data.get(f'{symbol}_orderbook_depth', 0)
        if orderbook_depth > 0:
            if order_volume > orderbook_depth * self.depth_ratio_limit:
                return self._create_result(
                    RiskAction.WARN,
                    f"订单量接近盘口深度，建议拆单",
                    order_volume=order_volume,
                    depth=orderbook_depth,
                    ratio=order_volume / orderbook_depth
                )
        
        return self._create_result(
            RiskAction.PASS,
            "流动性充足",
            order_volume=order_volume
        )


class R8_TradingTimeRule(RiskRule):
    """
    R8: 交易时间检查
    非交易时段禁止下单
    集合竞价期间禁止开仓
    支持按品种匹配不同夜盘交易时段
    """
    
    # 日盘交易时段（所有品种统一）
    DAY_SESSIONS = [
        (time(9, 0), time(10, 15)),   # 上午第一节
        (time(10, 30), time(11, 30)), # 上午第二节
        (time(13, 30), time(15, 0)),  # 下午
    ]
    
    # 集合竞价时段
    AUCTION_SESSIONS = [
        (time(8, 55), time(9, 0)),    # 早盘集合竞价
        (time(20, 55), time(21, 0)),  # 夜盘集合竞价
    ]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enable_night_session = config.get('enable_night_session', True)
        # 从 risk_rules.yaml 加载夜盘交易时段（支持按品种细分）
        night_sessions = config.get('night_sessions', [])
        if not night_sessions:
            night_sessions = self._load_night_sessions_from_yaml()
        self.night_sessions = self._build_night_sessions(night_sessions)
    
    @staticmethod
    def _load_night_sessions_from_yaml() -> List[Dict[str, Any]]:
        """从 config/risk_rules.yaml 加载夜盘交易时段"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "risk_rules.yaml"
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get('trading_sessions', {}).get('night', [])
        except Exception:
            return []
    
    @staticmethod
    def _parse_time(time_str: str) -> time:
        """解析 HH:MM 格式时间字符串"""
        parts = str(time_str).split(':')
        return time(int(parts[0]), int(parts[1]))
    
    def _build_night_sessions(self, raw_sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建夜盘交易时段列表"""
        result = []
        for s in raw_sessions:
            start = self._parse_time(s['start'])
            end = self._parse_time(s['end'])
            symbols = s.get('symbols', [])
            result.append({
                'start': start,
                'end': end,
                'symbols': [sym.upper() for sym in symbols] if symbols else [],
            })
        return result
    
    def _in_night_session(self, current_time: time, symbol: str) -> bool:
        """检查当前时间是否在指定品种的夜盘交易时段内"""
        base_symbol = ''.join(c for c in symbol if c.isalpha()).upper()
        for session in self.night_sessions:
            start = session['start']
            end = session['end']
            session_symbols = session['symbols']
            # 有 symbols 字段：仅适用于指定品种；无 symbols：适用于所有品种
            if session_symbols and base_symbol not in session_symbols:
                continue
            # 处理跨午夜（如 21:00-02:30）
            if end <= start:
                if current_time >= start or current_time <= end:
                    return True
            else:
                if start <= current_time <= end:
                    return True
        return False
    
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        now = datetime.now()
        current_time = now.time()
        symbol = order.symbol
        
        # 检查是否在集合竞价时段
        for start, end in self.AUCTION_SESSIONS:
            if start <= current_time <= end:
                if order.offset == "OPEN":
                    return self._create_result(
                        RiskAction.BLOCK,
                        f"集合竞价期间禁止开仓：{current_time.strftime('%H:%M')}",
                        current_time=current_time.strftime('%H:%M:%S')
                    )
                else:
                    return self._create_result(
                        RiskAction.PASS,
                        f"集合竞价期间允许平仓",
                        current_time=current_time.strftime('%H:%M:%S')
                    )
        
        # 检查日盘时段（所有品种统一）
        for start, end in self.DAY_SESSIONS:
            if start <= current_time <= end:
                return self._create_result(
                    RiskAction.PASS,
                    f"日盘交易时段：{current_time.strftime('%H:%M')}",
                    current_time=current_time.strftime('%H:%M:%S')
                )
        
        # 检查夜盘时段（按品种匹配）
        if self.enable_night_session and self.night_sessions:
            if self._in_night_session(current_time, symbol):
                return self._create_result(
                    RiskAction.PASS,
                    f"夜盘交易时段：{current_time.strftime('%H:%M')}，品种{symbol}",
                    current_time=current_time.strftime('%H:%M:%S'),
                    symbol=symbol
                )
        
        # 不在任何交易时段
        return self._create_result(
            RiskAction.BLOCK,
            f"非交易时段：{current_time.strftime('%H:%M')}，品种{symbol}",
            current_time=current_time.strftime('%H:%M:%S'),
            symbol=symbol
        )


class R3_PriceLimitRule(RiskRule):
    """
    R3: 涨跌停限制
    买入开仓：委托价格 >= 涨停价 → 拒绝
    卖出开仓：委托价格 <= 跌停价 → 拒绝
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        symbol = order.symbol
        
        # 获取涨跌停价格
        limit_up = context.market_data.get(f'{symbol}_limit_up', 0)
        limit_down = context.market_data.get(f'{symbol}_limit_down', 0)
        
        if not limit_up or not limit_down:
            return self._create_result(
                RiskAction.PASS,
                "无涨跌停数据，跳过检查",
                symbol=symbol
            )
        
        # 检查是否触及涨跌停
        if order.direction == "LONG" and order.offset == "OPEN":
            if order.price >= limit_up:
                return self._create_result(
                    RiskAction.BLOCK,
                    f"买入开仓价格{order.price} >= 涨停价{limit_up}",
                    price=order.price,
                    limit_up=limit_up
                )
        
        if order.direction == "SHORT" and order.offset == "OPEN":
            if order.price <= limit_down:
                return self._create_result(
                    RiskAction.BLOCK,
                    f"卖出开仓价格{order.price} <= 跌停价{limit_down}",
                    price=order.price,
                    limit_down=limit_down
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"价格{order.price}在涨跌停范围内[{limit_down}, {limit_up}]",
            price=order.price,
            limit_up=limit_up,
            limit_down=limit_down
        )




# ==================== Layer 2: 账户级风险 ====================

class R2_DailyLossLimitRule(RiskRule):
    """
    R2: 单日最大亏损限制
    当日累计亏损 >= 账户权益的2.5% 或 >= 5000元（取较大值）→ 禁止开仓
    仅检查开仓订单，平仓不受限制
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.limit_ratio = config.get('limit', 0.025)  # 2.5%
        self.absolute_min = config.get('absolute_min', 5000)  # 5000元
        
    def check(self, order, context):
        # 仅对开仓订单进行检查
        if order.offset != "OPEN":
            return self._create_result(
                RiskAction.PASS,
                "平仓订单，跳过单日亏损检查",
                symbol=order.symbol
            )
        
        # 获取账户权益和当日盈亏
        if not context.account:
            return self._create_result(
                RiskAction.PASS,
                "无账户信息，跳过单日亏损检查",
                symbol=order.symbol
            )
        
        equity = context.account.get('equity', 0)
        daily_pnl = context.account.get('daily_pnl', 0)  # 当日累计盈亏（负数为亏损）
        
        if equity <= 0:
            return self._create_result(
                RiskAction.PASS,
                "账户权益无效，跳过检查",
                equity=equity
            )
        
        # 计算亏损阈值（取比例和绝对值的较大值）
        threshold_ratio = equity * self.limit_ratio
        threshold = max(threshold_ratio, self.absolute_min)
        
        # 检查当日亏损是否超过阈值（daily_pnl为负表示亏损）
        if daily_pnl < 0 and abs(daily_pnl) >= threshold:
            return self._create_result(
                RiskAction.BLOCK,
                f"单日亏损超限：当日亏损{abs(daily_pnl):.0f}元 >= 阈值{threshold:.0f}元（权益{equity:.0f}的{self.limit_ratio*100:.1f}%或{self.absolute_min}元）",
                daily_pnl=daily_pnl,
                threshold=threshold,
                equity=equity,
                limit_ratio=self.limit_ratio,
                absolute_min=self.absolute_min
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"单日亏损检查通过：当日盈亏{daily_pnl:.0f}元，阈值{threshold:.0f}元",
            daily_pnl=daily_pnl,
            threshold=threshold
        )


class R7_ConsecutiveLossRule(RiskRule):
    """
    R7: 连续亏损次数限制
    连续亏损 >= 5次 → 暂停交易（禁止开仓）
    连续盈利 >= 3次 → 恢复交易
    仅检查开仓订单
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.base_limit = config.get('base', 5)  # 基础限制5次
        self.recover_after = config.get('recover_after', 3)  # 连续3次盈利恢复
        self.consecutive_losses = 0  # 当前连续亏损次数
        self.consecutive_wins = 0    # 当前连续盈利次数
        self.is_paused = False       # 是否暂停交易
        
    def update_trade_result(self, pnl):
        """更新交易结果（由外部调用）"""
        if pnl > 0:
            # 盈利
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            
            # 连续盈利达到恢复阈值，解除暂停
            if self.is_paused and self.consecutive_wins >= self.recover_after:
                self.is_paused = False
                self.consecutive_wins = 0
                
        elif pnl < 0:
            # 亏损
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            
            # 连续亏损达到限制，暂停交易
            if self.consecutive_losses >= self.base_limit:
                self.is_paused = True
        
        # pnl == 0 时不变
        
    def check(self, order, context):
        # 仅对开仓订单进行检查
        if order.offset != "OPEN":
            return self._create_result(
                RiskAction.PASS,
                "平仓订单，跳过连续亏损检查",
                symbol=order.symbol
            )
        
        # 检查是否处于暂停状态
        if self.is_paused:
            return self._create_result(
                RiskAction.BLOCK,
                f"交易暂停：连续亏损{self.consecutive_losses}次 >= 限制{self.base_limit}次，需连续盈利{self.recover_after}次恢复",
                consecutive_losses=self.consecutive_losses,
                limit=self.base_limit,
                recover_after=self.recover_after,
                consecutive_wins=self.consecutive_wins
            )
        
        # 检查是否即将达到限制（预警）
        if self.consecutive_losses >= self.base_limit - 1:
            return self._create_result(
                RiskAction.WARN,
                f"连续亏损预警：当前{self.consecutive_losses}次，再亏损1次将暂停交易",
                consecutive_losses=self.consecutive_losses,
                limit=self.base_limit
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"连续亏损检查通过：当前{self.consecutive_losses}次，限制{self.base_limit}次",
            consecutive_losses=self.consecutive_losses,
            limit=self.base_limit
        )


class R11_DispositionEffectRule(RiskRule):
    """
    R11: 处置效应监控
    亏损持仓占比 >= 50% 且试图反向开仓 → WARN（提示处置效应风险）
    基于行为金融学：投资者倾向于过早卖出盈利持仓、过久持有亏损持仓
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.drawdown_threshold = config.get('drawdown_threshold', 0.50)  # 50%
        
    def check(self, order, context):
        # 获取持仓盈亏信息
        if not context.positions:
            return self._create_result(
                RiskAction.PASS,
                "无持仓，跳过处置效应检查",
                symbol=order.symbol
            )
        
        # 计算亏损持仓占比
        total_positions = len(context.positions)
        losing_positions = 0
        
        for symbol, pos in context.positions.items():
            if pos == 0:
                continue
                
            # 获取持仓成本和当前价格
            cost_price = context.market_data.get(f'{symbol}_cost_price', 0)
            current_price = context.market_data.get(f'{symbol}_price', 0)
            
            if cost_price > 0 and current_price > 0:
                # 多头持仓：当前价 < 成本价 → 亏损
                if pos > 0 and current_price < cost_price:
                    losing_positions += 1
                # 空头持仓：当前价 > 成本价 → 亏损
                elif pos < 0 and current_price > cost_price:
                    losing_positions += 1
        
        # 计算亏损占比
        loss_ratio = losing_positions / total_positions if total_positions > 0 else 0
        
        # 检查是否触发处置效应预警
        if loss_ratio >= self.drawdown_threshold:
            # 检查是否是反向开仓（可能加剧处置效应）
            is_reverse = False
            current_symbol_pos = context.positions.get(order.symbol, 0)
            
            if current_symbol_pos != 0:
                # 当前有持仓，检查是否反向
                if (current_symbol_pos > 0 and order.direction == "SHORT" and order.offset == "OPEN") or \
                   (current_symbol_pos < 0 and order.direction == "LONG" and order.offset == "OPEN"):
                    is_reverse = True
            
            if is_reverse:
                return self._create_result(
                    RiskAction.WARN,
                    f"处置效应预警：亏损持仓占比{loss_ratio*100:.0f}% >= {self.drawdown_threshold*100:.0f}%，反向开仓可能加剧亏损",
                    loss_ratio=loss_ratio,
                    threshold=self.drawdown_threshold,
                    losing_positions=losing_positions,
                    total_positions=total_positions,
                    is_reverse=True
                )
            else:
                return self._create_result(
                    RiskAction.WARN,
                    f"处置效应提示：亏损持仓占比{loss_ratio*100:.0f}% >= {self.drawdown_threshold*100:.0f}%，建议审视持仓",
                    loss_ratio=loss_ratio,
                    threshold=self.drawdown_threshold,
                    losing_positions=losing_positions,
                    total_positions=total_positions,
                    is_reverse=False
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"处置效应检查通过：亏损持仓占比{loss_ratio*100:.0f}% < {self.drawdown_threshold*100:.0f}%",
            loss_ratio=loss_ratio,
            threshold=self.drawdown_threshold
        )

# ==================== Layer 3: 交易执行风险 ====================

class R1_PositionLimitRule(RiskRule):
    """
    R1: 单品种持仓限制（动态化）
    基于20日波动率动态调整：
    - 波动率 < 15%: 30%
    - 波动率 15-25%: 25%
    - 波动率 25-35%: 20%
    - 波动率 > 35%: 15%
    同板块品种聚类上限：40%
    """
    
    # 品种聚类（V6.1 §3.1.2）
    SECTOR_CLUSTERS = {
        'energy': ['SC', 'FU', 'LU', 'BU'],  # 能源化工
        'metal': ['CU', 'AL', 'ZN', 'NI', 'SN', 'AU', 'AG'],  # 有色金属
        'black': ['RB', 'HC', 'I', 'J', 'JM'],  # 黑色金属
        'agri': ['M', 'Y', 'P', 'OI', 'RM', 'A'],  # 农产品
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_ratio = config.get('base_ratio', 0.25)
        self.cluster_limit = config.get('cluster_limit', 0.40)
        self.volatility_thresholds = [
            (0.15, 0.30),  # (波动率上限, 持仓比例)
            (0.25, 0.25),
            (0.35, 0.20),
            (float('inf'), 0.15),
        ]
        
    def _get_volatility_ratio(self, symbol: str, context: RiskContext) -> float:
        """获取品种20日波动率"""
        vol = context.market_data.get(f'{symbol}_volatility_20d', 0)
        if vol > 0:
            return vol
        # 使用ATR估算
        atr = context.market_data.get(f'{symbol}_atr_14', 0)
        price = context.market_data.get(f'{symbol}_price', 1)
        if atr > 0 and price > 0:
            return (atr / price) * np.sqrt(20)  # 年化近似
        return 0.20  # 默认20%
    
    def _get_position_limit(self, volatility: float) -> float:
        """根据波动率计算持仓上限"""
        for threshold, ratio in self.volatility_thresholds:
            if volatility <= threshold:
                return ratio
        return 0.15
    
    def _get_sector(self, symbol: str) -> Optional[str]:
        """获取品种所属板块"""
        # 提取品种代码（去掉年份月份）
        base_symbol = ''.join([c for c in symbol if c.isalpha()])
        for sector, symbols in self.SECTOR_CLUSTERS.items():
            if base_symbol in symbols:
                return sector
        return None
    
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        symbol = order.symbol
        
        # 获取当前持仓
        current_pos = context.positions.get(symbol, 0)
        
        # 计算开仓后的总持仓
        if order.offset == "OPEN":
            if order.direction == "LONG":
                new_pos = current_pos + order.volume
            else:  # SHORT
                new_pos = current_pos - order.volume
        else:  # CLOSE
            new_pos = current_pos  # 平仓不增加持仓
        
        # 获取账户权益
        equity = context.account.get('equity', 100000) if context.account else 100000
        
        # 获取当前价格
        price = context.market_data.get(f'{symbol}_price', order.price)
        
        # 计算持仓市值比例
        position_value = abs(new_pos) * price
        position_ratio = position_value / equity if equity > 0 else 0
        
        # 获取波动率并计算限制
        volatility = self._get_volatility_ratio(symbol, context)
        limit = self._get_position_limit(volatility)
        
        # 检查单品种限制
        if position_ratio > limit:
            return self._create_result(
                RiskAction.BLOCK,
                f"单品种持仓超限：{symbol} 持仓比例{position_ratio*100:.1f}% > 限制{limit*100:.1f}%（波动率{volatility*100:.1f}%）",
                symbol=symbol,
                position_ratio=position_ratio,
                limit=limit,
                volatility=volatility
            )
        
        # 检查板块聚类限制
        sector = self._get_sector(symbol)
        if sector:
            sector_positions = []
            for sym, pos in context.positions.items():
                if self._get_sector(sym) == sector:
                    sym_price = context.market_data.get(f'{sym}_price', 0)
                    sector_positions.append(abs(pos) * sym_price)
            
            # 加上当前订单
            if order.offset == "OPEN":
                sector_positions.append(order.volume * price)
            
            sector_value = sum(sector_positions)
            sector_ratio = sector_value / equity if equity > 0 else 0
            
            if sector_ratio > self.cluster_limit:
                return self._create_result(
                    RiskAction.BLOCK,
                    f"板块持仓超限：{sector} 板块比例{sector_ratio*100:.1f}% > 限制{self.cluster_limit*100:.1f}%",
                    sector=sector,
                    sector_ratio=sector_ratio,
                    limit=self.cluster_limit
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"持仓检查通过：{symbol} 比例{position_ratio*100:.1f}% <= 限制{limit*100:.1f}%",
            position_ratio=position_ratio,
            limit=limit
        )


class R4_TotalMarginRule(RiskRule):
    """
    R4: 总保证金占用上限（分时段）
    交易时段：70%
    收盘前15分钟：60%
    隔夜缓冲：历史最大跳空 + 5%
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.trading_limit = config.get('trading_limit', 0.70)
        self.closing_limit = config.get('closing_limit', 0.60)
        self.closing_window = config.get('closing_window', 15)  # 收盘前15分钟
        self.safety_buffer = config.get('safety_buffer', 0.05)
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        # 获取当前时间
        now = datetime.now()
        current_time = now.time()
        
        # 判断时段
        # 下午收盘时间 15:00
        closing_start = time(14, 45)  # 收盘前15分钟
        
        if closing_start <= current_time <= time(15, 0):
            limit = self.closing_limit
            period = "收盘前"
        else:
            limit = self.trading_limit
            period = "交易时段"
        
        # 获取账户信息
        if context.account:
            used_margin = context.account.get('used_margin', 0)
            available = context.account.get('available', 0)
            total = used_margin + available
        else:
            return self._create_result(
                RiskAction.PASS,
                "无账户信息，跳过保证金检查",
                symbol=order.symbol
            )
        
        # 计算订单所需保证金（简化：使用10%保证金率）
        order_margin = order.volume * order.price * 0.10
        
        # 计算总保证金占用
        total_margin = used_margin + order_margin
        margin_ratio = total_margin / total if total > 0 else 0
        
        # 检查是否超过限制
        if margin_ratio > limit:
            return self._create_result(
                RiskAction.BLOCK,
                f"保证金超限：{period}占用{margin_ratio*100:.1f}% > 限制{limit*100:.1f}%",
                margin_ratio=margin_ratio,
                limit=limit,
                period=period
            )
        
        # 隔夜缓冲检查（夜盘前）
        night_start = time(20, 45)
        if night_start <= current_time <= time(21, 0):
            # 获取历史最大跳空
            max_gap = context.market_data.get('max_overnight_gap', 0.03)
            required_buffer = max_gap + self.safety_buffer
            available_buffer = 1 - margin_ratio
            
            if available_buffer < required_buffer:
                return self._create_result(
                    RiskAction.WARN,
                    f"隔夜缓冲不足：可用{available_buffer*100:.1f}% < 需要{required_buffer*100:.1f}%（历史跳空{max_gap*100:.1f}%）",
                    available_buffer=available_buffer,
                    required_buffer=required_buffer
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"保证金检查通过：{period}占用{margin_ratio*100:.1f}% <= 限制{limit*100:.1f}%",
            margin_ratio=margin_ratio,
            limit=limit
        )


class R9_CapitalAdequacyRule(RiskRule):
    """
    R9: 资金充足性检查
    可用资金 >= 冻结资金 + 预冻结 + 5%安全缓冲
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.safety_buffer = config.get('safety_buffer', 0.05)
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        if not context.account:
            return self._create_result(
                RiskAction.PASS,
                "无账户信息，跳过资金检查",
                symbol=order.symbol
            )
        
        available = context.account.get('available', 0)
        frozen = context.account.get('frozen', 0)
        pre_frozen = context.account.get('pre_frozen', 0)
        
        # 计算订单所需资金
        order_value = order.volume * order.price
        
        # 计算安全缓冲
        total_required = frozen + pre_frozen + order_value
        buffer_needed = total_required * self.safety_buffer
        min_available = total_required + buffer_needed
        
        if available < min_available:
            return self._create_result(
                RiskAction.BLOCK,
                f"资金不足：可用{available:.0f} < 需要{min_available:.0f}（含{self.safety_buffer*100:.0f}%缓冲）",
                available=available,
                required=min_available,
                frozen=frozen,
                pre_frozen=pre_frozen
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"资金充足：可用{available:.0f} >= 需要{min_available:.0f}",
            available=available,
            required=min_available
        )


class R12_CancelLimitRule(RiskRule):
    """
    R12: 撤单次数限制
    60分钟内撤单次数 >= 阈值（默认10）→ BLOCK
    预警线：达到阈值 80% → WARN
    支持 simulate（实时检查）和 precheck（下单前预检）两种模式
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_cancel = config.get('max_cancel', 10)  # 60分钟内撤单上限
        self.window_minutes = config.get('window_minutes', 60)  # 检查窗口（分钟）
        
    def check(self, order: OrderRequest, context: RiskContext) -> RiskResult:
        symbol = order.symbol
        
        # 从 context 获取撤单次数（由上层通过 market_data 注入）
        # 键名约定：cancel_count_60m 或 {symbol}_cancel_count_60m
        cancel_count = context.market_data.get(
            f'{symbol}_cancel_count_60m',
            context.market_data.get('cancel_count_60m', 0)
        )
        
        if cancel_count >= self.max_cancel:
            return self._create_result(
                RiskAction.BLOCK,
                f"撤单次数超限：{symbol} 60分钟内撤单{cancel_count}次 >= 阈值{self.max_cancel}次",
                symbol=symbol,
                cancel_count=cancel_count,
                threshold=self.max_cancel,
                window_minutes=self.window_minutes
            )
        
        # 预警线：达到阈值的 80%
        warn_threshold = int(self.max_cancel * 0.8)
        if cancel_count >= warn_threshold:
            return self._create_result(
                RiskAction.WARN,
                f"撤单次数预警：{symbol} 60分钟内撤单{cancel_count}次，接近阈值{self.max_cancel}次",
                symbol=symbol,
                cancel_count=cancel_count,
                threshold=self.max_cancel,
                warn_threshold=warn_threshold
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"撤单次数正常：{symbol} 60分钟内撤单{cancel_count}次 < 阈值{self.max_cancel}次",
            symbol=symbol,
            cancel_count=cancel_count,
            threshold=self.max_cancel
        )


# ==================== Risk Engine ====================

class RiskEngine:
    """
    风控引擎主类
    按优先级顺序执行规则链
    """
    
    # 规则执行顺序（V6.1 §4）
    RULE_ORDER = [
        'R8',   # 交易时间检查
        'R10',  # 宏观熔断
        'R3',   # 涨跌停限制
        'R5',   # 波动率异常过滤
        'R6',   # 流动性检查
        'R9',   # 资金充足性检查
        'R2',   # 单日最大亏损
        'R7',   # 连续亏损次数限制
        'R11',  # 处置效应监控
        'R12',  # 撤单次数限制
        'R1',   # 单品种持仓限制
        'R4',   # 总保证金占用上限
    ]
    
    def __init__(self, profile: str = 'moderate', state_path: str = "config/risk_state.json"):
        """
        初始化风控引擎
        
        Args:
            profile: 风险画像 - conservative/moderate/aggressive
            state_path: 风控状态持久化文件路径
        """
        self.profile = profile
        self.config = self._load_config(profile)
        self.rules = self._init_rules()
        self.rule_instances = {r.rule_id: r for r in self.rules}
        # 加载统一 YAML 规则定义（Layer + Severity 映射）
        self._rules = self._load_risk_rules()
        # 状态持久化
        self._state_path = state_path
        self._last_save_time: float = 0.0
        self._save_interval: float = 5.0  # 最小保存间隔（秒）
        # 自动加载历史状态
        self.load_state(state_path)

    def _load_risk_rules(self) -> List[Dict[str, Any]]:
        """从 risk/rules/risk_rules.yaml 加载规则定义"""
        try:
            rules_path = Path(__file__).parent.parent.parent / "risk" / "rules" / "risk_rules.yaml"
            with open(rules_path, encoding="utf-8") as f:
                return yaml.safe_load(f).get("rules", [])
        except Exception:
            return []

    def get_layer(self, rule_id: str) -> int:
        """返回 numeric layer (1/2/3)，替代字符串 L1/L2/L3/L4/L5"""
        for r in self._rules:
            if r.get("id") == rule_id:
                return r.get("layer", 2)  # 默认 Layer 2
        return 2

    def get_severity(self, rule_id: str) -> str:
        """返回统一 severity: PASS / WARN / BLOCK"""
        for r in self._rules:
            if r.get("id") == rule_id:
                layer = r.get("layer", 2)
                return LAYER_TO_SEVERITY.get(layer, "WARN")
        return "WARN"

    def get_r10_threshold(self) -> float:
        """返回 R10 宏观熔断阈值（从 YAML 读取）"""
        for r in self._rules:
            if r.get("id") == "R10":
                return float(r.get("threshold", -0.5))
        return -0.5
        
    def _load_config(self, profile: str) -> Dict[str, Any]:
        """加载风控配置"""
        # 默认配置
        base_config = {
            'R10': {'enabled': True, 'fuse_low': 30, 'fuse_high': 70, 'hysteresis': 5},
            'R5': {'enabled': True, 'warn_multiplier': 2.0, 'block_multiplier': 3.0, 'lookback_days': 20},
            'R6': {'enabled': True, 'volume_ratio_limit': 0.05, 'depth_ratio_limit': 0.30},
            'R8': {'enabled': True, 'enable_night_session': True},
            'R3': {'enabled': True},
            'R1': {'enabled': False, 'base_ratio': 0.25},  # 默认关闭
            'R4': {'enabled': True, 'limit': 0.70},
            'R9': {'enabled': True, 'safety_buffer': 0.05},
            'R2': {'enabled': True, 'limit': 0.025, 'absolute_min': 5000},
            'R7': {'enabled': True, 'base': 5},
            'R11': {'enabled': True, 'drawdown_threshold': 0.50},
            'R12': {'enabled': True, 'max_cancel': 10, 'window_minutes': 60},
        }
        
        # 根据画像调整
        profile_adjustments = {
            'conservative': {
                'R1': {'enabled': False, 'base_ratio': 0.15},
                'R2': {'limit': 0.015, 'absolute_min': 3000},
                'R4': {'limit': 0.50},
                'R7': {'base': 3},
            },
            'moderate': {
                'R1': {'enabled': False, 'base_ratio': 0.25},
                'R2': {'limit': 0.025, 'absolute_min': 5000},
                'R4': {'limit': 0.70},
                'R7': {'base': 5},
            },
            'aggressive': {
                'R1': {'enabled': False, 'base_ratio': 0.35},
                'R2': {'limit': 0.040, 'absolute_min': 10000},
                'R4': {'limit': 0.85},
                'R7': {'base': 7},
            }
        }
        
        adjustments = profile_adjustments.get(profile, {})
        for rule_id, adj in adjustments.items():
            if rule_id in base_config:
                base_config[rule_id].update(adj)
        
        return base_config
    
    def _init_rules(self) -> List[RiskRule]:
        """初始化规则实例"""
        rule_classes = {
            'R10': R10_MacroFuseRule,
            'R5': R5_VolatilityFilterRule,
            'R6': R6_LiquidityCheckRule,
            'R8': R8_TradingTimeRule,
            'R3': R3_PriceLimitRule,
            'R2': R2_DailyLossLimitRule,
            'R7': R7_ConsecutiveLossRule,
            'R11': R11_DispositionEffectRule,
            'R1': R1_PositionLimitRule,
            'R4': R4_TotalMarginRule,
            'R9': R9_CapitalAdequacyRule,
            'R12': R12_CancelLimitRule,
        }
        
        rules = []
        for rule_id, rule_class in rule_classes.items():
            config = self.config.get(rule_id, {'enabled': False})
            rules.append(rule_class(config))
        
        return rules
    
    def check_order(self, order: OrderRequest, context: Optional[RiskContext] = None) -> List[RiskResult]:
        """
        检查订单
        
        Returns:
            List[RiskResult]: 所有规则检查结果
        """
        if context is None:
            context = RiskContext()
        
        results = []
        
        for rule_id in self.RULE_ORDER:
            if rule_id not in self.rule_instances:
                continue
                
            rule = self.rule_instances[rule_id]
            if not rule.is_enabled():
                continue
            
            result = rule.check(order, context)
            results.append(result)
            
            if result.action == RiskAction.BLOCK:
                # 被拦截，停止后续检查
                break
            elif result.action == RiskAction.WARN:
                # 记录警告，继续检查
                context.add_warning(result)
        
        # 每轮风控检查后自动保存状态（频率受限）
        self._auto_save_state()
        
        return results
    
    def can_trade(self, order: OrderRequest, context: Optional[RiskContext] = None) -> bool:
        """
        快速检查是否可以交易
        
        Returns:
            bool: True if can trade, False otherwise
        """
        results = self.check_order(order, context)
        return all(r.action != RiskAction.BLOCK for r in results)
    
    # ==================== 状态持久化 ====================
    
    def save_state(self, path: Optional[str] = None) -> bool:
        """
        将风控状态序列化到 JSON 文件。
        
        Args:
            path: 保存路径，默认使用 self._state_path
            
        Returns:
            bool: 是否保存成功
        """
        path = path or self._state_path
        now = time_mod.time()
        
        # 频率限制：至少 5 秒间隔
        if now - self._last_save_time < self._save_interval:
            return True
        
        try:
            # 收集各规则状态
            counters = {}
            timers = {}
            flags = {}
            
            # R7: 连续亏损状态
            r7 = self.rule_instances.get('R7')
            if r7 and isinstance(r7, R7_ConsecutiveLossRule):
                counters['R7_consecutive_losses'] = r7.consecutive_losses
                counters['R7_consecutive_wins'] = r7.consecutive_wins
                flags['R7_is_paused'] = r7.is_paused
            
            # R10: 宏观熔断状态
            r10 = self.rule_instances.get('R10')
            if r10 and isinstance(r10, R10_MacroFuseRule):
                timers['R10_last_trigger_score'] = r10.last_trigger_score
            
            # R12: 撤单计数（从外部注入，这里保存快照）
            # cancel_count / cancel_timestamps 由上层管理，此处记录版本信息
            
            state = {
                "version": 1,
                "updated_at": datetime.now().isoformat(),
                "profile": self.profile,
                "counters": counters,
                "timers": timers,
                "flags": flags,
            }
            
            # 写入文件（原子写：先写临时文件再重命名）
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = save_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            tmp_path.replace(save_path)
            
            self._last_save_time = now
            return True
            
        except Exception as e:
            logger.warning("风控状态保存失败: %s", e, exc_info=True)
            return False
    
    def load_state(self, path: Optional[str] = None) -> bool:
        """
        从 JSON 文件恢复风控状态。
        
        Args:
            path: 加载路径，默认使用 self._state_path
            
        Returns:
            bool: 是否加载成功
        """
        path = path or self._state_path
        state_file = Path(path)
        
        if not state_file.exists():
            return False
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            version = state.get('version', 0)
            if version != 1:
                logger.warning("风控状态文件版本不匹配: %s (期望 1)", version)
                return False
            
            counters = state.get('counters', {})
            timers = state.get('timers', {})
            flags = state.get('flags', {})
            
            # 恢复 R7 状态
            r7 = self.rule_instances.get('R7')
            if r7 and isinstance(r7, R7_ConsecutiveLossRule):
                r7.consecutive_losses = counters.get('R7_consecutive_losses', 0)
                r7.consecutive_wins = counters.get('R7_consecutive_wins', 0)
                r7.is_paused = flags.get('R7_is_paused', False)
            
            # 恢复 R10 状态
            r10 = self.rule_instances.get('R10')
            if r10 and isinstance(r10, R10_MacroFuseRule):
                r10.last_trigger_score = timers.get('R10_last_trigger_score', None)
            
            updated_at = state.get('updated_at', '未知')
            logger.info("风控状态已恢复 (更新时间: %s)", updated_at)
            return True
            
        except Exception as e:
            logger.warning("风控状态加载失败: %s", e, exc_info=True)
            return False
    
    def _auto_save_state(self) -> None:
        """自动保存状态（频率受限，失败不阻断）"""
        try:
            self.save_state()
        except Exception as e:
            logger.debug("自动保存状态异常: %s", e)


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试风控引擎
    print("="*60)
    print("Risk Engine Test")
    print("="*60)
    
    # 创建引擎
    engine = RiskEngine(profile='moderate')
    print(f"\nRisk Profile: {engine.profile}")
    print(f"Rules: {[r.rule_id for r in engine.rules]}")
    
    # 创建测试订单
    order = OrderRequest(
        symbol="RU2505",
        exchange="SHFE",
        direction="LONG",
        offset="OPEN",
        price=15000.0,
        volume=1
    )
    
    # 创建上下文（含测试数据）
    context = RiskContext(
        account={
            'equity': 100000,
            'available': 80000,
            'used_margin': 15000,
            'frozen': 5000,
            'pre_frozen': 0,
        },
        positions={
            'RU2505': 1,  # 当前持仓1手
        },
        market_data={
            'macro_score': 50,  # 中性
            'RU2505_atr_14': 300,
            'RU2505_price': 15000,
            'RU2505_atr_history': [200] * 20,  # 历史ATR较低
            'RU2505_avg_volume_20d': 100000,
            'RU2505_limit_up': 16000,
            'RU2505_limit_down': 14000,
            'RU2505_volatility_20d': 0.18,  # 18%波动率
        }
    )
    
    # 检查订单
    print("\n[Test 1] Normal order")
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试宏观熔断
    print("\n[Test 2] Macro fuse (score=20, LONG)")
    context.market_data['macro_score'] = 20
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试涨跌停
    print("\n[Test 3] Price limit (price=16500)")
    order.price = 16500
    context.market_data['macro_score'] = 50
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试波动率
    print("\n[Test 4] Volatility (ATR=900, price=15000)")
    order.price = 15000
    context.market_data['RU2505_atr_14'] = 900  # 6% ATR
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试持仓限制（R1）
    print("\n[Test 5] Position limit (high volatility)")
    context.market_data['RU2505_atr_14'] = 300
    context.market_data['RU2505_volatility_20d'] = 0.40  # 40%高波动
    order.volume = 5  # 开仓5手
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试保证金限制（R4）
    print("\n[Test 6] Margin limit (low available)")
    context.market_data['RU2505_volatility_20d'] = 0.18
    order.volume = 1
    context.account['available'] = 1000  # 可用资金很少
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    # 测试资金充足性（R9）
    print("\n[Test 7] Capital adequacy (insufficient)")
    context.account['available'] = 500  # 资金不足
    context.account['used_margin'] = 50000
    results = engine.check_order(order, context)
    for r in results:
        print(f"  {r.rule_id}: {r.action.value} - {r.message}")
    print(f"  Can trade: {engine.can_trade(order, context)}")
    
    print("\n" + "="*60)
    print("Test completed")
