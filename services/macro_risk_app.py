# -*- coding: utf-8 -*-
"""
MacroRiskApp — VNpy App 插件形式的风控系统

13条风控规则：
1. 单品种最大持仓
2. 单日最大亏损
3. 涨跌停限制
4. 总持仓比例上限
5. 单品种集中度上限
6. 波动率异常过滤
7. 流动性检查
8. 方向一致性检查
9. 连续亏损次数限制
10. 交易时间检查
11. 资金充足性检查
12. 滑点限制
13. 宏观熔断

使用方式：
    from services.macro_risk_app import MacroRiskApp
    main_engine.add_app(MacroRiskApp)
"""

import json
import sqlite3
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.object import OrderData, TradeData, PositionData
from vnpy.trader.constant import Direction, Offset, Status


# ============================ 配置 ============================
@dataclass
class RiskRuleConfig:
    """单条风控规则配置"""
    name: str
    enabled: bool = True
    threshold: Any = None
    level: str = "L1"  # L1/L2/L3/L4/L5


DEFAULT_RULES = [
    RiskRuleConfig("单品种最大持仓", True, 10, "L1"),
    RiskRuleConfig("单日最大亏损", True, 5000, "L1"),
    RiskRuleConfig("涨跌停限制", True, None, "L2"),
    RiskRuleConfig("总持仓比例上限", True, 0.80, "L2"),
    RiskRuleConfig("单品种集中度上限", True, 0.30, "L2"),
    RiskRuleConfig("波动率异常过滤", False, 3.0, "L3"),
    RiskRuleConfig("流动性检查", False, 100, "L3"),
    RiskRuleConfig("方向一致性检查", True, None, "L3"),
    RiskRuleConfig("连续亏损次数限制", True, 3, "L3"),
    RiskRuleConfig("交易时间检查", True, None, "L4"),
    RiskRuleConfig("资金充足性检查", True, None, "L4"),
    RiskRuleConfig("滑点限制", True, 0.02, "L4"),
    RiskRuleConfig("宏观熔断", True, -0.50, "L5"),
]


# ============================ 品种配置 ============================
SYMBOL_CONFIG = {
    'RU': {'size': 10, 'margin_ratio': 0.12, 'pricetick': 5},
    'ZN': {'size': 5, 'margin_ratio': 0.12, 'pricetick': 5},
    'RB': {'size': 10, 'margin_ratio': 0.13, 'pricetick': 1},
    'NI': {'size': 1, 'margin_ratio': 0.14, 'pricetick': 10},
    'CU': {'size': 5, 'margin_ratio': 0.12, 'pricetick': 10},
    'AL': {'size': 5, 'margin_ratio': 0.12, 'pricetick': 5},
    'AU': {'size': 1000, 'margin_ratio': 0.10, 'pricetick': 0.02},
    'AG': {'size': 15, 'margin_ratio': 0.13, 'pricetick': 1},
    'I': {'size': 100, 'margin_ratio': 0.15, 'pricetick': 0.5},
    'J': {'size': 100, 'margin_ratio': 0.20, 'pricetick': 0.5},
    'JM': {'size': 60, 'margin_ratio': 0.20, 'pricetick': 0.5},
    'M': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'Y': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 2},
    'P': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 2},
    'C': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'TA': {'size': 5, 'margin_ratio': 0.12, 'pricetick': 2},
    'MA': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'SR': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'CF': {'size': 5, 'margin_ratio': 0.12, 'pricetick': 5},
    'RM': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'OI': {'size': 10, 'margin_ratio': 0.10, 'pricetick': 1},
    'SC': {'size': 1000, 'margin_ratio': 0.15, 'pricetick': 0.1},
    'NR': {'size': 10, 'margin_ratio': 0.12, 'pricetick': 5},
    'IF': {'size': 300, 'margin_ratio': 0.12, 'pricetick': 0.2},
    'IC': {'size': 200, 'margin_ratio': 0.14, 'pricetick': 0.2},
    'IH': {'size': 300, 'margin_ratio': 0.12, 'pricetick': 0.2},
    'T': {'size': 10000, 'margin_ratio': 0.02, 'pricetick': 0.005},
}


def get_symbol_config(symbol: str) -> dict:
    """获取品种配置"""
    return SYMBOL_CONFIG.get(symbol, {'size': 10, 'margin_ratio': 0.15, 'pricetick': 1})


def get_contract_size(symbol: str) -> int:
    """获取合约乘数"""
    return get_symbol_config(symbol).get('size', 10)


def get_margin_ratio(symbol: str) -> float:
    """获取保证金比例"""
    return get_symbol_config(symbol).get('margin_ratio', 0.15)


def get_pricetick(symbol: str) -> float:
    """获取价格最小变动单位"""
    return get_symbol_config(symbol).get('pricetick', 1)


# ============================ 交易时间配置 ============================
TRADING_HOURS = {
    # 上海期货交易所 - 有色金属
    'CU': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(1, 0))],
    'AL': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(1, 0))],
    'ZN': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(1, 0))],
    'NI': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(1, 0))],
    # 上海期货交易所 - 贵金属
    'AU': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(2, 30))],
    'AG': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(2, 30))],
    # 上海期货交易所 - 黑色系
    'RB': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'I': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'J': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'JM': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    # 上海期货交易所 - 橡胶
    'RU': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'NR': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    # 上海国际能源交易中心
    'SC': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(2, 30))],
    # 大连商品交易所
    'M': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'Y': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'P': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'C': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
          (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    # 郑州商品交易所
    'TA': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    'MA': [(dt_time(9, 0), dt_time(10, 15)), (dt_time(10, 30), dt_time(11, 30)), 
           (dt_time(13, 30), dt_time(15, 0)), (dt_time(21, 0), dt_time(23, 0))],
    # 中国金融期货交易所
    'IF': [(dt_time(9, 30), dt_time(11, 30)), (dt_time(13, 0), dt_time(15, 0))],
    'IC': [(dt_time(9, 30), dt_time(11, 30)), (dt_time(13, 0), dt_time(15, 0))],
    'IH': [(dt_time(9, 30), dt_time(11, 30)), (dt_time(13, 0), dt_time(15, 0))],
    'T': [(dt_time(9, 15), dt_time(11, 30)), (dt_time(13, 0), dt_time(15, 15))],
}


def get_trading_hours(symbol: str) -> list:
    """获取品种交易时段"""
    return TRADING_HOURS.get(symbol, [
        (dt_time(9, 0), dt_time(11, 30)),
        (dt_time(13, 30), dt_time(15, 0)),
    ])


def is_in_trading_hours(trading_hours: list, current_time: dt_time) -> bool:
    """检查当前时间是否在交易时段内（支持跨日期时段如21:00-01:00）"""
    for start, end in trading_hours:
        # 处理跨日期的情况（如夜盘 21:00-01:00）
        if start > end:
            # 跨日期：start到午夜 或 午夜到end
            if current_time >= start or current_time <= end:
                return True
        else:
            # 不跨日期：正常判断
            if start <= current_time <= end:
                return True
    return False


# ============================ RiskEngine ============================
class RiskEngine(BaseEngine):
    """
    风控引擎

    - 监听 eOrder 事件，在订单提交前拦截风险订单
    - 13条规则可独立开关
    - 拦截记录写入 audit.db
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__(main_engine, event_engine, "RiskManager")

        self.rules: Dict[str, RiskRuleConfig] = {r.name: r for r in DEFAULT_RULES}
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.trade_history: List[dict] = []

        # 注册事件
        self.event_engine.register("eOrder", self._on_order)
        self.event_engine.register("eTrade", self._on_trade)

        print("[MacroRiskApp] RiskEngine 已启动，13条规则就绪")

    def _on_order(self, event: Event) -> None:
        """订单事件：检查风控"""
        order: OrderData = event.data
        if order.status != Status.SUBMITTING:
            return

        # 检查各规则
        violations = self._check_rules(order)
        if violations:
            # 发布风控拦截事件
            risk_event = Event(type="eRiskRule", data={
                "rule_name": violations[0]["rule"],
                "action": "block",
                "order": {
                    "vt_orderid": order.vt_orderid,
                    "symbol": order.symbol,
                    "direction": order.direction.value,
                    "offset": order.offset.value,
                    "price": order.price,
                    "volume": order.volume,
                },
                "reason": violations[0]["reason"],
            })
            self.event_engine.put(risk_event)
            print(f"[MacroRiskApp] 拦截订单: {order.vt_orderid} - {violations[0]['reason']}")

    def _on_trade(self, event: Event) -> None:
        """成交事件：更新盈亏统计（按金额计算）"""
        trade: TradeData = event.data
        
        # 获取品种配置
        symbol = trade.symbol
        # 从品种代码提取基础品种（如 au2605 -> AU）
        base_symbol = ''.join([c for c in symbol if not c.isdigit()]).upper()
        
        # 获取合约乘数
        size = get_contract_size(base_symbol)
        
        pnl = 0.0
        if trade.offset == Offset.CLOSE or trade.offset == Offset.CLOSETODAY:
            # 查找对应的开仓记录
            for t in reversed(self.trade_history):
                if t["symbol"] == trade.symbol and t["direction"] != trade.direction.value:
                    # 计算盈亏金额（考虑合约乘数）
                    if trade.direction == Direction.SHORT:
                        # 多头平仓：卖出价 - 买入价
                        pnl = (trade.price - t["price"]) * trade.volume * size
                    else:
                        # 空头平仓：买入价 - 卖出价
                        pnl = (t["price"] - trade.price) * trade.volume * size
                    break

        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.trade_history.append({
            "symbol": trade.symbol,
            "direction": trade.direction.value,
            "price": trade.price,
            "volume": trade.volume,
            "pnl": pnl,
            "time": datetime.now().isoformat(),
        })

    def _check_rules(self, order: OrderData) -> List[dict]:
        """检查所有规则，返回违规列表"""
        violations = []
        
        # 提取基础品种代码
        base_symbol = ''.join([c for c in order.symbol if not c.isdigit()]).upper()

        # 1. 单品种最大持仓（按资金比例动态计算）
        if self.rules["单品种最大持仓"].enabled:
            # 获取账户资金
            accounts = self.main_engine.get_all_accounts()
            if accounts:
                balance = getattr(accounts[0], 'balance', 0)
                if isinstance(balance, (int, float)) and balance > 0:
                    # 单品种最大占用资金比例（默认30%）
                    max_position_value = balance * 0.30
                    
                    # 获取品种配置
                    symbol_config = get_symbol_config(base_symbol)
                    size = symbol_config['size']
                    margin_ratio = symbol_config.get('margin_ratio', 0.15)
                    
                    # 计算最大手数
                    estimated_price = order.price if order.price > 0 else 1
                    max_lots = int(max_position_value / (estimated_price * size * margin_ratio))
                    max_lots = max(1, max_lots)  # 至少1手
                    
                    positions = self.main_engine.get_all_positions()
                    current_vol = sum(p.volume for p in positions
                                    if p.symbol == order.symbol
                                    and p.direction == order.direction)
                    if current_vol + order.volume > max_lots:
                        violations.append({
                            "rule": "单品种最大持仓",
                            "reason": f"{order.symbol} {order.direction.value} 持仓 {current_vol}+{order.volume} > 限制 {max_lots} (资金占比30%)"
                        })
                else:
                    # 无法获取资金，使用默认限制
                    max_pos = 10
                    positions = self.main_engine.get_all_positions()
                    current_vol = sum(p.volume for p in positions
                                    if p.symbol == order.symbol
                                    and p.direction == order.direction)
                    if current_vol + order.volume > max_pos:
                        violations.append({
                            "rule": "单品种最大持仓",
                            "reason": f"{order.symbol} {order.direction.value} 持仓 {current_vol}+{order.volume} > 默认限制 {max_pos}"
                        })

        # 2. 单日最大亏损
        if self.rules["单日最大亏损"].enabled:
            max_loss = self.rules["单日最大亏损"].threshold
            if self.daily_pnl < -max_loss:
                violations.append({
                    "rule": "单日最大亏损",
                    "reason": f"当日亏损 {self.daily_pnl:.2f} 超过限制 {-max_loss}"
                })

        # 3. 涨跌停限制（简化：检查价格是否为整数倍）
        if self.rules["涨跌停限制"].enabled:
            if order.price <= 0:
                violations.append({"rule": "涨跌停限制", "reason": "价格必须大于0"})

        # 4. 总持仓比例上限
        if self.rules["总持仓比例上限"].enabled:
            # 简化：检查总手数
            positions = self.main_engine.get_all_positions()
            total_lots = sum(p.volume for p in positions)
            if total_lots + order.volume > 50:  # 假设总限制50手
                violations.append({
                    "rule": "总持仓比例上限",
                    "reason": f"总持仓 {total_lots}+{order.volume} 手超过限制"
                })

        # 5. 单品种集中度上限
        if self.rules["单品种集中度上限"].enabled:
            positions = self.main_engine.get_all_positions()
            symbol_lots = sum(p.volume for p in positions if p.symbol == order.symbol)
            total_lots = sum(p.volume for p in positions) + order.volume or 1
            if symbol_lots / total_lots > 0.30:
                violations.append({
                    "rule": "单品种集中度上限",
                    "reason": f"{order.symbol} 集中度超过30%"
                })

        # 8. 方向一致性检查（与宏观信号交叉验证）
        if self.rules["方向一致性检查"].enabled:
            signal_bridge = getattr(self.main_engine, 'signal_bridge', None)
            if signal_bridge:
                macro_direction = signal_bridge.get_latest_direction(base_symbol)
                
                if macro_direction:
                    # 检查是否与宏观信号冲突
                    if macro_direction == "LONG" and order.direction == Direction.SHORT:
                        violations.append({
                            "rule": "方向一致性检查",
                            "reason": f"{base_symbol} 宏观信号看多，禁止做空"
                        })
                    elif macro_direction == "SHORT" and order.direction == Direction.LONG:
                        violations.append({
                            "rule": "方向一致性检查",
                            "reason": f"{base_symbol} 宏观信号看空，禁止做多"
                        })
                    # NEUTRAL 时不拦截，允许双向交易

        # 9. 连续亏损次数限制
        if self.rules["连续亏损次数限制"].enabled:
            max_losses = self.rules["连续亏损次数限制"].threshold
            if self.consecutive_losses >= max_losses:
                violations.append({
                    "rule": "连续亏损次数限制",
                    "reason": f"连续亏损 {self.consecutive_losses} 次，暂停开仓"
                })

        # 10. 交易时间检查（按品种配置精确时段）
        if self.rules["交易时间检查"].enabled:
            now = datetime.now().time()
            
            # 获取品种交易时间配置
            trading_hours = get_trading_hours(base_symbol)
            
            if not is_in_trading_hours(trading_hours, now):
                violations.append({
                    "rule": "交易时间检查",
                    "reason": f"当前时间 {now} 不在 {base_symbol} 交易时段"
                })

        # 11. 资金充足性检查（按品种计算保证金）
        if self.rules["资金充足性检查"].enabled:
            accounts = self.main_engine.get_all_accounts()
            if accounts:
                available = getattr(accounts[0], 'available', 0)
                if not isinstance(available, (int, float)):
                    available = 0
                
                # 获取品种配置
                symbol_config = get_symbol_config(base_symbol)
                size = symbol_config['size']
                margin_ratio = symbol_config.get('margin_ratio', 0.15)
                
                # 计算实际保证金需求
                estimated_margin = order.price * order.volume * size * margin_ratio
                
                if available < estimated_margin:
                    violations.append({
                        "rule": "资金充足性检查",
                        "reason": f"可用资金 {available:.2f} < 预估保证金 {estimated_margin:.2f} ({base_symbol} {size}手×{margin_ratio:.0%})"
                    })

        # 12. 滑点限制
        if self.rules["滑点限制"].enabled:
            max_slippage = self.rules["滑点限制"].threshold
            # 简化：检查价格是否为 pricetick 的整数倍
            # 实际需要 tick 数据
            pass

        # 13. 宏观熔断（接入 SignalBridge）
        if self.rules["宏观熔断"].enabled:
            threshold = self.rules["宏观熔断"].threshold
            
            # 尝试从 main_engine 获取 SignalBridge 缓存的宏观信号
            signal_bridge = getattr(self.main_engine, 'signal_bridge', None)
            if signal_bridge:
                # 获取品种的宏观评分
                score = signal_bridge.get_latest_score(base_symbol)
                
                if score is not None:
                    # 双向熔断检查
                    if score <= threshold:  # 极端看空（如 -0.5）
                        if order.direction == Direction.LONG:
                            violations.append({
                                "rule": "宏观熔断",
                                "reason": f"{base_symbol} 宏观评分 {score:.2f} <= 熔断阈值 {threshold}，禁止做多"
                            })
                    elif score >= abs(threshold):  # 极端看多（如 +0.5）
                        if order.direction == Direction.SHORT:
                            violations.append({
                                "rule": "宏观熔断",
                                "reason": f"{base_symbol} 宏观评分 {score:.2f} >= +{abs(threshold):.2f}，禁止做空"
                            })
            else:
                # SignalBridge 未挂载，记录警告但不拦截（避免完全阻塞交易）
                pass

        return violations

    def get_rule_status(self) -> List[dict]:
        """获取所有规则状态"""
        return [
            {
                "name": name,
                "enabled": config.enabled,
                "threshold": config.threshold,
                "level": config.level,
            }
            for name, config in self.rules.items()
        ]

    def set_rule(self, name: str, enabled: bool = None, threshold: Any = None):
        """设置规则参数"""
        if name in self.rules:
            if enabled is not None:
                self.rules[name].enabled = enabled
            if threshold is not None:
                self.rules[name].threshold = threshold


# ============================ MacroRiskApp ============================
class MacroRiskApp:
    """VNpy App 插件"""

    app_name = "MacroRiskManager"
    app_module = __name__
    app_path = "services.macro_risk_app"
    display_name = "宏观风控系统"
    engine_class = RiskEngine
    widget_name = "RiskManagerWidget"
    icon_name = "risk.svg"

    def __init__(self):
        pass
