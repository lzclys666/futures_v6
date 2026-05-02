"""
多因子加权评分策略 (V6.0 正式版 + 审计日志集成)
因子：趋势(MA偏离)、动量(RSI)、波动(ATR变化)、成交量(量比)
市场状态识别：ADX区分趋势/震荡，动态调整因子权重
兼容：观察池参数管理器、止盈止损托管模块
新增：自动记录策略创建、参数修改等审计日志
"""

import os
import re
from datetime import time, datetime
from typing import Optional

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
import talib
import numpy as np


class MultiFactorStrategy(CtaTemplate):
    """多因子加权评分策略"""

    author = "V6_Developer"

    # ---------- 策略参数 ----------
    ma_period = 20
    rsi_period = 14
    atr_period = 14
    volume_ma_period = 20
    adx_period = 14

    long_threshold = 0.5
    short_threshold = -0.5

    weight_trend = 0.4
    weight_momentum = 0.3
    weight_volatility = 0.2
    weight_volume = 0.1

    fixed_volume = 1

    observe_weight_coef = 0.3
    observe_stop_mult = 1.3

    stop_loss_atr_mult = 2.0
    take_profit_atr_mult = 3.0

    local_monitor_symbols = "jm,lh,zn,br,sa,ec"

    parameters = [
        "ma_period",
        "rsi_period",
        "atr_period",
        "volume_ma_period",
        "adx_period",
        "long_threshold",
        "short_threshold",
        "weight_trend",
        "weight_momentum",
        "weight_volatility",
        "weight_volume",
        "fixed_volume",
        "observe_weight_coef",
        "observe_stop_mult",
        "stop_loss_atr_mult",
        "take_profit_atr_mult",
        "local_monitor_symbols"
    ]

    # ---------- 实时变量 ----------
    current_score = 0.0
    market_regime = "transition"
    current_status = ""
    gateway_connected = True

    variables = [
        "current_score",
        "market_regime",
        "current_status",
        "gateway_connected"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager(size=100)

        raw_symbol = vt_symbol.split('.')[0]
        match = re.match(r"([a-zA-Z]+)", raw_symbol)
        self.symbol = match.group(1).lower() if match else raw_symbol.lower()

        self.instrument_profiles = self.load_instrument_profiles()
        self.profile = self.instrument_profiles.get(self.symbol, {})
        raw_status = self.profile.get("status", "whitelist")

        if raw_status in ["observe", "观察池", "observe_pool"]:
            self.current_status = "observe"
        elif raw_status in ["blacklist", "黑名单"]:
            self.current_status = "blacklist"
        else:
            self.current_status = "whitelist"

        local_list = [s.strip() for s in self.local_monitor_symbols.split(",")]
        self.use_local_monitor = self.symbol in local_list

        self.active_stop_orders = {}
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

        # ==================== 审计日志集成 ====================
        main_engine = self.cta_engine.main_engine
        self.audit_svc = getattr(main_engine, 'audit_service', None)
        if self.audit_svc:
            self.audit_svc.log_audit(
                operator="admin",  # 可替换为实际用户名
                operation_type="strategy_created",
                target_type="strategy",
                target_id=self.strategy_name,
                extra_data={
                    "vt_symbol": vt_symbol,
                    "initial_params": setting,
                    "status": self.current_status
                }
            )

        self.write_log(f"[INIT] 品种={self.symbol}, 状态={self.current_status}, 模式={'本地监控' if self.use_local_monitor else 'CTP条件单'}")

    def load_instrument_profiles(self) -> dict:
        home_path = os.path.expanduser("~")
        config_path = os.path.join(home_path, ".vntrader", "instrument_profiles.json")
        if os.path.exists(config_path):
            return load_json(config_path)
        else:
            self.write_log("[警告] 未找到品种配置文件")
            return {}

    def on_setting_changed(self, setting: dict):
        """当策略参数通过GUI被修改时，此方法会被自动调用（VNPY 内部回调）"""
        if self.audit_svc:
            old_params = {k: getattr(self, k) for k in self.parameters}
            self.audit_svc.log_audit(
                operator="admin",
                operation_type="strategy_params_modified",
                target_type="strategy",
                target_id=self.strategy_name,
                old_value=old_params,
                new_value=setting
            )
        # 应用新参数
        for key, value in setting.items():
            setattr(self, key, value)

    def on_init(self):
        self.write_log("策略初始化")
        self.load_bar(30)

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

        close = am.close
        high = am.high
        low = am.low
        volume = am.volume

        ma20 = talib.SMA(close, self.ma_period)
        if ma20[-1] == 0:
            return
        trend_score = (close[-1] / ma20[-1] - 1) * 100

        rsi = talib.RSI(close, self.rsi_period)
        if np.isnan(rsi[-1]):
            return
        momentum_score = (rsi[-1] - 50) / 50

        atr = talib.ATR(high, low, close, self.atr_period)
        if atr[-1] == 0:
            return
        atr_ma = talib.SMA(atr, self.atr_period)
        if atr_ma[-1] == 0:
            return
        vol_score = (atr[-1] / atr_ma[-1] - 1) * 2

        volume_ma = talib.SMA(volume, self.volume_ma_period)
        if volume_ma[-1] == 0:
            return
        volume_score = (volume[-1] / volume_ma[-1] - 1)

        adx = talib.ADX(high, low, close, self.adx_period)
        if np.isnan(adx[-1]):
            return
        adx_value = adx[-1]
        if adx_value > 25:
            self.market_regime = "trend"
        elif adx_value < 20:
            self.market_regime = "range"
        else:
            self.market_regime = "transition"

        w_trend = self.weight_trend
        w_momentum = self.weight_momentum
        w_vol = self.weight_volatility
        w_volume = self.weight_volume

        if self.market_regime == "trend":
            w_trend += 0.2
            w_momentum -= 0.1
        elif self.market_regime == "range":
            w_trend -= 0.2
            w_momentum += 0.2

        total = w_trend + w_momentum + w_vol + w_volume
        w_trend /= total
        w_momentum /= total
        w_vol /= total
        w_volume /= total

        self.current_score = (
            w_trend * trend_score +
            w_momentum * momentum_score +
            w_vol * vol_score +
            w_volume * volume_score
        )

        if self.current_score >= self.long_threshold:
            self.process_signal(bar, "LONG", self.current_score)
        elif self.current_score <= self.short_threshold:
            self.process_signal(bar, "SHORT", self.current_score)

        self.put_event()

    def process_signal(self, bar: BarData, signal_type: str, score: float):
        if self.current_status == "blacklist":
            self.write_log(f"黑名单拦截，评分={score:.2f}")
            return

        now = datetime.now().time()
        in_day_ban = (time(8, 55) <= now <= time(9, 5))
        in_night_ban = (time(20, 55) <= now <= time(21, 5))
        if in_day_ban or in_night_ban:
            self.write_log("集合竞价时段，禁止开仓")
            return

        self.cancel_all_stop_orders()

        volume = self.calculate_volume()
        price = bar.close_price + 2 if signal_type == "LONG" else bar.close_price - 2

        self.write_log(f"信号触发：{signal_type}，评分={score:.2f}，手数={volume}，市场状态={self.market_regime}")

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

        atr = self.am.atr(self.atr_period)
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
        if stop_order.status in [Status.CANCELLED, Status.ALLTRADED]:
            self.active_stop_orders.pop(stop_order.stop_orderid, None)
        else:
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