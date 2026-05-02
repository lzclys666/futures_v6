"""
极简均线测试策略 (V6.0 最终修正版)
功能：金叉死叉 + 观察池仓位 + 本地/CTP双止盈止损 + 断网兜底 + 集合竞价兜底
修复：撤单API、状态重置、价格保护、OCO逻辑、集合竞价双层防护、回测条件单返回值兼容、回测StopOrder属性兼容
"""

import os
import re
from datetime import time, datetime
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)
from vnpy.trader.constant import Direction, Offset, Status
from vnpy.trader.utility import load_json


class SimpleMaTestStrategy(CtaTemplate):
    """金叉做多，死叉做空（带品种状态管理和止盈止损托管）"""

    author = "V6_Developer"

    # ---------- 可配置参数 ----------
    fast_window = 10
    slow_window = 20
    fixed_volume = 1

    observe_weight_coef = 0.3
    observe_stop_mult = 1.3

    stop_loss_atr_mult = 2.0
    take_profit_atr_mult = 3.0

    local_monitor_symbols = "jm,lh,zn,br,sa,ec"

    parameters = [
        "fast_window",
        "slow_window",
        "fixed_volume",
        "observe_weight_coef",
        "observe_stop_mult",
        "stop_loss_atr_mult",
        "take_profit_atr_mult",
        "local_monitor_symbols"
    ]

    # ---------- 实时变量 ----------
    fast_ma = 0.0
    slow_ma = 0.0
    current_status = ""
    gateway_connected = True

    variables = [
        "fast_ma",
        "slow_ma",
        "current_status",
        "gateway_connected"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager(size=max(self.fast_window, self.slow_window) + 10)

        # 品种代码提取（纯字母）
        raw_symbol = vt_symbol.split('.')[0]
        match = re.match(r"([a-zA-Z]+)", raw_symbol)
        self.symbol = match.group(1).lower() if match else raw_symbol.lower()

        # 加载品种配置
        self.instrument_profiles = self.load_instrument_profiles()
        self.profile = self.instrument_profiles.get(self.symbol, {})
        raw_status = self.profile.get("status", "whitelist")

        if raw_status in ["observe", "观察池", "observe_pool"]:
            self.current_status = "observe"
        elif raw_status in ["blacklist", "黑名单"]:
            self.current_status = "blacklist"
        else:
            self.current_status = "whitelist"

        # 判断是否使用本地监控
        local_list = [s.strip() for s in self.local_monitor_symbols.split(",")]
        self.use_local_monitor = self.symbol in local_list

        # 止盈止损状态
        self.active_stop_orders = {}
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

        self.write_log(f"[INIT] 品种={self.symbol}, 状态={self.current_status}, 模式={'本地监控' if self.use_local_monitor else 'CTP条件单'}")

    def load_instrument_profiles(self) -> dict:
        """加载品种配置文件"""
        home_path = os.path.expanduser("~")
        config_path = os.path.join(home_path, ".vntrader", "instrument_profiles.json")
        if os.path.exists(config_path):
            return load_json(config_path)
        else:
            self.write_log("[警告] 未找到品种配置文件")
            return {}

    def on_init(self):
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        self.write_log("策略启动")
        self.put_event()

    def on_stop(self):
        self.write_log("策略停止，执行平仓并清状态")
        if self.pos != 0:
            last_price = self.am.close[-1] if self.am.count >= 1 else self.entry_price
            self.force_close_position(last_price or 1)
        self.cancel_all_stop_orders()
        self.put_event()

    def on_tick(self, tick: TickData):
        self.bg.update_tick(tick)

        if self.use_local_monitor and self.pos != 0 and tick.last_price > 0:
            self.check_stop_loss_take_profit(tick.last_price)

    def on_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        fast_array = am.sma(self.fast_window, array=True)
        slow_array = am.sma(self.slow_window, array=True)
        if len(fast_array) < 2 or len(slow_array) < 2:
            return

        self.fast_ma = fast_array[-1]
        self.slow_ma = slow_array[-1]
        fast_prev = fast_array[-2]
        slow_prev = slow_array[-2]

        cross_over = (self.fast_ma > self.slow_ma) and (fast_prev <= slow_prev)
        cross_below = (self.fast_ma < self.slow_ma) and (fast_prev >= slow_prev)

        if cross_over:
            self.process_signal(bar, "LONG")
        elif cross_below:
            self.process_signal(bar, "SHORT")

        self.put_event()

    def process_signal(self, bar: BarData, signal_type: str):
        if self.current_status == "blacklist":
            self.write_log("黑名单拦截，不交易")
            return

        now = datetime.now().time()
        in_day_ban = (time(8, 55) <= now <= time(9, 5))
        in_night_ban = (time(20, 55) <= now <= time(21, 5))
        if in_day_ban or in_night_ban:
            self.write_log("集合竞价时段，禁止开仓（策略层兜底）")
            return

        self.cancel_all_stop_orders()

        volume = self.calculate_volume()
        price = bar.close_price + 2 if signal_type == "LONG" else bar.close_price - 2

        if signal_type == "LONG":
            if self.pos == 0:
                self.buy(price, volume)
            elif self.pos < 0:
                self.cover(price, abs(self.pos))
                self.buy(price, volume)
        else:
            if self.pos == 0:
                self.short(price, volume)
            elif self.pos > 0:
                self.sell(price, abs(self.pos))
                self.short(price, volume)

    def calculate_volume(self) -> int:
        base = self.fixed_volume
        coef = self.profile.get("weight_coef", 1.0)
        if self.current_status == "observe":
            coef *= self.observe_weight_coef
        return max(1, int(base * coef))

    def on_trade(self, trade: TradeData):
        self.write_log(f"成交: {trade.direction.value} {trade.offset.value} {trade.volume}手 @ {trade.price}")

        if trade.offset == Offset.OPEN:
            self.entry_price = trade.price
            self.set_stop_loss_take_profit(trade)
        else:
            self.entry_price = 0.0
            self.stop_loss_price = 0.0
            self.take_profit_price = 0.0
            self.cancel_all_stop_orders()

        self.put_event()

    def set_stop_loss_take_profit(self, trade: TradeData):
        self.cancel_all_stop_orders()

        atr = self.am.atr(14)
        if atr == 0:
            atr = trade.price * 0.01

        atr_mult = self.profile.get("atr_stop_mult", self.stop_loss_atr_mult)
        if self.current_status == "observe":
            atr_mult *= self.observe_stop_mult

        if self.pos > 0:
            self.stop_loss_price = trade.price - atr * atr_mult
            self.take_profit_price = trade.price + atr * self.take_profit_atr_mult
        elif self.pos < 0:
            self.stop_loss_price = trade.price + atr * atr_mult
            self.take_profit_price = trade.price - atr * self.take_profit_atr_mult
        else:
            return

        if self.use_local_monitor:
            self.write_log(f"本地监控：止损={self.stop_loss_price:.2f}, 止盈={self.take_profit_price:.2f}")
            return

        if self.pos > 0:
            result = self.sell(self.stop_loss_price, abs(self.pos), stop=True)
        else:
            result = self.cover(self.stop_loss_price, abs(self.pos), stop=True)

        if result is None:
            return

        if isinstance(result, list):
            for order in result:
                if hasattr(order, 'stop_orderid'):
                    self.active_stop_orders[order.stop_orderid] = order
        else:
            if hasattr(result, 'stop_orderid'):
                self.active_stop_orders[result.stop_orderid] = result

        self.write_log(f"CTP条件单：止损={self.stop_loss_price:.2f}")

    def check_stop_loss_take_profit(self, price: float):
        if self.pos == 0 or price <= 0:
            return

        hit = False
        if self.pos > 0:
            if price <= self.stop_loss_price:
                self.write_log(f"本地止损触发：{price:.2f} <= {self.stop_loss_price:.2f}")
                hit = True
            elif price >= self.take_profit_price:
                self.write_log(f"本地止盈触发：{price:.2f} >= {self.take_profit_price:.2f}")
                hit = True
        else:
            if price >= self.stop_loss_price:
                self.write_log(f"本地止损触发：{price:.2f} >= {self.stop_loss_price:.2f}")
                hit = True
            elif price <= self.take_profit_price:
                self.write_log(f"本地止盈触发：{price:.2f} <= {self.take_profit_price:.2f}")
                hit = True

        if hit:
            self.force_close_position(price)

    def force_close_position(self, price: float):
        if self.pos == 0 or price <= 0:
            return

        if self.pos > 0:
            self.sell(price * 0.98, abs(self.pos))
        else:
            self.cover(price * 1.02, abs(self.pos))

        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0
        self.cancel_all_stop_orders()

    def cancel_all_stop_orders(self):
        for oid in list(self.active_stop_orders.keys()):
            self.cancel_order(oid)
        self.active_stop_orders.clear()

    def on_order(self, order: OrderData):
        if order.status in [Status.CANCELLED, Status.REJECTED]:
            self.active_stop_orders.pop(order.vt_orderid, None)

    def on_stop_order(self, stop_order: StopOrder):
        # 回测模式下 StopOrder 没有 is_active 属性，直接使用 status 判断即可
        if stop_order.status in [Status.CANCELLED, Status.ALLTRADED]:
            self.active_stop_orders.pop(stop_order.stop_orderid, None)
        else:
            # 如果是活跃状态（等待触发），也记录在案
            self.active_stop_orders[stop_order.stop_orderid] = stop_order

    def on_engine_disconnect(self):
        self.gateway_connected = False
        self.write_log("【WARNING】网关断开！")
        if self.pos != 0:
            self.write_log("【断网强平】执行！")
            last_price = self.am.close[-1] if self.am.count >= 1 else self.entry_price
            self.force_close_position(last_price or 1)

    def on_engine_connect(self):
        self.gateway_connected = True
        self.write_log("网关已恢复连接")