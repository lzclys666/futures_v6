# strategies/macro_demo_strategy.py
from config.paths import MACRO_ENGINE
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.constant import Direction, Offset, Status
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator, ArrayManager
from services.signal_bridge import EVENT_MACRO_SIGNAL


# 品种配置映射表
SYMBOL_CONFIG = {
    # 上海期货交易所
    'RU': {'exchange': 'SHFE', 'name': '天然橡胶', 'size': 10, 'pricetick': 5},
    'ZN': {'exchange': 'SHFE', 'name': '沪锌', 'size': 5, 'pricetick': 5},
    'RB': {'exchange': 'SHFE', 'name': '螺纹钢', 'size': 10, 'pricetick': 1},
    'NI': {'exchange': 'SHFE', 'name': '沪镍', 'size': 1, 'pricetick': 10},
    'CU': {'exchange': 'SHFE', 'name': '沪铜', 'size': 5, 'pricetick': 10},
    'AL': {'exchange': 'SHFE', 'name': '沪铝', 'size': 5, 'pricetick': 5},
    'AU': {'exchange': 'SHFE', 'name': '黄金', 'size': 1000, 'pricetick': 0.02},
    'AG': {'exchange': 'SHFE', 'name': '白银', 'size': 15, 'pricetick': 1},
    # 大连商品交易所
    'I': {'exchange': 'DCE', 'name': '铁矿石', 'size': 100, 'pricetick': 0.5},
    'J': {'exchange': 'DCE', 'name': '焦炭', 'size': 100, 'pricetick': 0.5},
    'JM': {'exchange': 'DCE', 'name': '焦煤', 'size': 60, 'pricetick': 0.5},
    'M': {'exchange': 'DCE', 'name': '豆粕', 'size': 10, 'pricetick': 1},
    'Y': {'exchange': 'DCE', 'name': '豆油', 'size': 10, 'pricetick': 2},
    'P': {'exchange': 'DCE', 'name': '棕榈油', 'size': 10, 'pricetick': 2},
    'C': {'exchange': 'DCE', 'name': '玉米', 'size': 10, 'pricetick': 1},
    # 郑州商品交易所
    'TA': {'exchange': 'CZCE', 'name': 'PTA', 'size': 5, 'pricetick': 2},
    'MA': {'exchange': 'CZCE', 'name': '甲醇', 'size': 10, 'pricetick': 1},
    'SR': {'exchange': 'CZCE', 'name': '白糖', 'size': 10, 'pricetick': 1},
    'CF': {'exchange': 'CZCE', 'name': '棉花', 'size': 5, 'pricetick': 5},
    'RM': {'exchange': 'CZCE', 'name': '菜粕', 'size': 10, 'pricetick': 1},
    'OI': {'exchange': 'CZCE', 'name': '菜油', 'size': 10, 'pricetick': 1},
    # 上海国际能源交易中心
    'SC': {'exchange': 'INE', 'name': '原油', 'size': 1000, 'pricetick': 0.1},
    'NR': {'exchange': 'INE', 'name': '20号胶', 'size': 10, 'pricetick': 5},
    # 中国金融期货交易所
    'IF': {'exchange': 'CFFEX', 'name': '沪深300', 'size': 300, 'pricetick': 0.2},
    'IC': {'exchange': 'CFFEX', 'name': '中证500', 'size': 200, 'pricetick': 0.2},
    'IH': {'exchange': 'CFFEX', 'name': '上证50', 'size': 300, 'pricetick': 0.2},
    'T': {'exchange': 'CFFEX', 'name': '10年期国债', 'size': 10000, 'pricetick': 0.005},
}


class MacroDemoStrategy(CtaTemplate):
    """宏观CTA策略：读取CSV宏观信号，结合技术指标进行共振交易"""

    author = "Demo"

    fast_window = 10
    slow_window = 20
    use_macro = True
    csv_path_str = str(MACRO_ENGINE / "output" / "{symbol}_macro_daily_{date}.csv")
    
    # 风控开关
    enable_stop_loss = True      # 固定止损开关
    enable_take_profit = True    # 固定止盈开关
    enable_trailing_stop = True  # 移动止损开关
    enable_tech_exit = True      # 技术反转平仓开关
    
    # 风控参数（单位：元/手 - 实际盈亏金额）
    stop_loss = 5000      # 止损：每手亏损5000元平仓
    take_profit = 10000   # 止盈：每手盈利10000元平仓
    trailing_stop = 3000  # 移动止损：盈利后回撤3000元/手平仓

    parameters = ["fast_window", "slow_window", "use_macro", "csv_path_str", 
                  "enable_stop_loss", "enable_take_profit", "enable_trailing_stop", "enable_tech_exit",
                  "stop_loss", "take_profit", "trailing_stop"]
    variables = ["macro_direction", "macro_score", "tech_direction", "entry_price", "highest_price", "lowest_price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.vt_symbol = vt_symbol
        self.symbol = self.extract_symbol(vt_symbol)
        
        # 获取品种配置
        self.symbol_config = self.get_symbol_config(self.symbol)
        
        self.macro_direction = "NEUTRAL"
        self.macro_score = 50.0

        # 初始化时不设置固定路径，在on_init和on_1min_bar中动态加载
        self.csv_path = None

        self.tech_direction = "NEUTRAL"
        self.bg = BarGenerator(self.on_bar, 1, self.on_1min_bar)
        self.am = ArrayManager()

        # 止损止盈相关
        self.entry_price = 0.0      # 开仓价格
        self.highest_price = 0.0    # 持仓期间最高价（用于移动止损）
        self.lowest_price = 0.0     # 持仓期间最低价（用于移动止损）

        self._csv_missing_warned = False
        self._position_synced = False  # CTP持仓同步标志

        # SignalBridge 事件驱动信号缓存
        self._latest_signals: dict = {}       # {symbol: event_data_dict}
        self._signal_last_update: dict = {}   # {symbol: datetime}

    def extract_symbol(self, vt_symbol: str) -> str:
        """从vt_symbol提取品种代码"""
        base = vt_symbol.split('.')[0]
        # 移除数字，保留字母部分
        symbol = ''.join([c for c in base if not c.isdigit()]).upper()
        return symbol
    
    def get_symbol_config(self, symbol: str) -> dict:
        """获取品种配置"""
        config = SYMBOL_CONFIG.get(symbol)
        if config is None:
            self.write_log_safe(f"[WARNING] Unknown symbol: {symbol}, using default config")
            # 默认配置
            config = {'exchange': 'UNKNOWN', 'name': symbol, 'size': 10, 'pricetick': 1}
        return config
    
    def write_log_safe(self, msg: str):
        """安全写入日志（处理编码问题）"""
        if self.cta_engine is None:
            # 测试模式，直接打印
            print(f"[LOG] {msg}")
            return
        try:
            # 尝试直接输出
            self.write_log(msg)
        except UnicodeEncodeError:
            # 如果失败，尝试编码转换
            try:
                safe_msg = msg.encode('utf-8').decode('utf-8')
                self.write_log(safe_msg)
            except:
                # 最后尝试ASCII编码
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                self.write_log(safe_msg)

    def on_init(self):
        self.write_log_safe(f"[INIT] Macro strategy init, symbol: {self.vt_symbol} -> {self.symbol}")
        self.write_log_safe(f"[INIT] Symbol config: {self.symbol_config}")
        self.write_log_safe(f"[INIT] CSV path template: {self.csv_path_str}")
        self.write_log_safe(f"[INIT] Macro filter: {'ON' if self.use_macro else 'OFF'}")
        # 初始化时加载一次（实盘模式用当前日期）
        self.load_macro_signal()

    def on_start(self):
        """策略启动 - 同步CTP持仓状态 + 注册SignalBridge事件"""
        self.write_log_safe("[START] 策略启动")
        self.sync_position_from_ctp()

        # 注册 SignalBridge 宏观信号事件
        try:
            if self.cta_engine is not None and hasattr(self.cta_engine, 'event_engine'):
                self.cta_engine.event_engine.register(
                    EVENT_MACRO_SIGNAL, self.on_signal_update
                )
                self.write_log_safe(f"[START] 已注册 SignalBridge 事件: {EVENT_MACRO_SIGNAL}")
            else:
                self.write_log_safe("[START] cta_engine 或 event_engine 不可用，跳过事件注册")
        except Exception as e:
            self.write_log_safe(f"[WARNING] SignalBridge 事件注册失败: {e}")

    def sync_position_from_ctp(self):
        """
        从CTP查询当前持仓并同步self.pos。
        
        策略重启后self.pos重置为0，但CTP账户可能有未平仓合约。
        此方法在on_start()中调用，从MainEngine的持仓缓存中查询实际持仓。
        
        多个查询路径（优先级从高到低）：
        1. vnpy_bridge.positions（FastAPI桥接器缓存）
        2. main_engine.positions（VNpy主引擎缓存）
        """
        try:
            if self.cta_engine is None:
                self.write_log_safe("[SYNC] 测试模式，跳过持仓同步")
                self._position_synced = True
                return

            # --- 路径1: vnpy_bridge ---
            bridge = getattr(self.cta_engine, 'vnpy_bridge', None)
            if bridge is None:
                # 尝试通过main_engine获取
                main_engine = getattr(self.cta_engine, 'main_engine', None)
                if main_engine:
                    bridge = getattr(main_engine, 'vnpy_bridge', None)

            if bridge and hasattr(bridge, 'positions'):
                positions = bridge.positions
                long_vol = 0
                short_vol = 0
                avg_price = 0.0
                prices = []
                for key, pos in positions.items():
                    # 精确匹配或品种前缀匹配（兼容主力连续 vs 具体合约）
                    if key == self.vt_symbol or key.startswith(self.symbol):
                        if str(getattr(pos, 'direction', '')) == 'Direction.LONG':
                            long_vol += pos.volume
                            if pos.price > 0:
                                prices.append((pos.volume, pos.price))
                        elif str(getattr(pos, 'direction', '')) == 'Direction.SHORT':
                            short_vol += pos.volume
                            if pos.price > 0:
                                prices.append((pos.volume, pos.price))

                net_pos = long_vol - short_vol
                if net_pos != 0:
                    self.pos = net_pos
                    # 用成交量加权均价作为开仓价
                    if prices:
                        total_vol = sum(v for v, _ in prices)
                        if total_vol > 0:
                            self.entry_price = sum(v * p for v, p in prices) / total_vol
                    self.write_log_safe(f"[SYNC] 恢复持仓: pos={self.pos}, entry_price={self.entry_price:.2f}")
                else:
                    self.write_log_safe("[SYNC] CTP无持仓，pos=0")
                self._position_synced = True
                return

            # --- 路径2: main_engine.positions ---
            main_engine = getattr(self.cta_engine, 'main_engine', None)
            if main_engine and hasattr(main_engine, 'positions'):
                positions = main_engine.positions
                long_vol = 0
                short_vol = 0
                avg_price = 0.0
                prices = []
                for key, pos in positions.items():
                    if key == self.vt_symbol or key.startswith(self.symbol):
                        if str(getattr(pos, 'direction', '')) == 'Direction.LONG':
                            long_vol += pos.volume
                            if pos.price > 0:
                                prices.append((pos.volume, pos.price))
                        elif str(getattr(pos, 'direction', '')) == 'Direction.SHORT':
                            short_vol += pos.volume
                            if pos.price > 0:
                                prices.append((pos.volume, pos.price))

                net_pos = long_vol - short_vol
                if net_pos != 0:
                    self.pos = net_pos
                    if prices:
                        total_vol = sum(v for v, _ in prices)
                        if total_vol > 0:
                            self.entry_price = sum(v * p for v, p in prices) / total_vol
                    self.write_log_safe(f"[SYNC] 恢复持仓: pos={self.pos}, entry_price={self.entry_price:.2f}")
                else:
                    self.write_log_safe("[SYNC] CTP无持仓，pos=0")
                self._position_synced = True
                return

            self.write_log_safe("[WARNING] 无法访问持仓数据源，跳过同步")
            self._position_synced = True  # 不阻止启动

        except Exception as e:
            self.write_log_safe(f"[ERROR] 持仓同步失败: {e}，使用默认pos=0")
            self._position_synced = True  # 不阻止启动

    def on_signal_update(self, event):
        """处理 SignalBridge 推送的宏观信号事件"""
        try:
            data = event.data
            symbol = data.get("symbol", "")
            direction = data.get("direction", "NEUTRAL")
            score = data.get("score", 0.0)

            self._latest_signals[symbol] = data
            self._signal_last_update[symbol] = datetime.now()

            print(f"[SignalBridge] 收到信号更新: {symbol} -> {direction}")
            self.write_log_safe(
                f"[SignalBridge] 事件信号: {symbol} -> {direction}, score={score:.4f}"
            )
        except Exception as e:
            self.write_log_safe(f"[ERROR] on_signal_update 处理异常: {e}")

    def _try_apply_event_signal(self) -> bool:
        """
        尝试使用事件驱动的信号数据。

        返回 True 表示已成功应用事件信号（跳过 CSV）。
        返回 False 表示事件信号不可用或已过期，需 fallback 到 CSV。

        有效性规则：
        - _latest_signals 中有当前品种数据
        - 最后更新时间在 30 分钟以内
        """
        data = self._latest_signals.get(self.symbol)
        if data is None:
            return False

        last_update = self._signal_last_update.get(self.symbol)
        if last_update is None:
            return False

        # 30 分钟超时检查
        elapsed = (datetime.now() - last_update).total_seconds()
        if elapsed > 1800:  # 30 * 60 秒
            return False

        # 应用事件信号
        new_dir = data.get("direction", "NEUTRAL")
        new_score = data.get("score", 0.0)
        if new_dir != self.macro_direction:
            self.macro_direction = new_dir
            self.macro_score = new_score
            self.write_log_safe(
                f"[MACRO-Event] {self.symbol} direction updated: {self.macro_direction}, "
                f"score: {self.macro_score:.2f}"
            )
        else:
            self.macro_score = new_score
        return True

    def on_timer(self):
        self.load_macro_signal()

    def load_macro_signal(self, bar_datetime=None):
        """加载宏观信号，支持回测时传入bar的时间"""
        # 动态替换路径占位符
        if bar_datetime is not None:
            # 回测模式：使用bar的时间
            date_str = bar_datetime.strftime("%Y%m%d")
        else:
            # 实盘模式：使用当前时间
            date_str = datetime.now().strftime("%Y%m%d")
        
        # 使用 os.path 替代 pathlib，避免路径解析问题
        import os
        csv_path_str = self.csv_path_str.format(symbol=self.symbol, date=date_str)
        csv_path = os.path.normpath(csv_path_str)
        
        if not os.path.exists(csv_path):
            # Fallback: 往前找最近交易日的 CSV（最多 5 天）
            fallback_date = None
            if bar_datetime is not None:
                base_dt = bar_datetime
            else:
                base_dt = datetime.now()

            for i in range(1, 6):
                prev_date = base_dt - timedelta(days=i)
                # 跳过周末
                if prev_date.weekday() >= 5:
                    continue
                prev_date_str = prev_date.strftime("%Y%m%d")
                prev_csv = self.csv_path_str.format(symbol=self.symbol, date=prev_date_str)
                prev_csv = os.path.normpath(prev_csv)
                if os.path.exists(prev_csv):
                    csv_path = prev_csv
                    fallback_date = prev_date_str
                    break

            if fallback_date is None:
                if bar_datetime is None and not self._csv_missing_warned:
                    self.write_log_safe(f"[WARNING] CSV file not found for today or recent trading days: {self.symbol}")
                    self._csv_missing_warned = True
                return
            else:
                if bar_datetime is None:
                    self.write_log_safe(f"[INFO] Using fallback CSV from {fallback_date} for {self.symbol}")

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 兼容 camelCase(rowType) 和 snake_case(row_type)
                    row_type = row.get('row_type', '') or row.get('rowType', '')
                    # 兼容 BOM 前缀的 symbol 字段
                    row_symbol = row.get('symbol', '') or row.get('\ufeffsymbol', '')
                    if row_type == 'SUMMARY' and row_symbol == self.symbol:
                        new_dir = row['direction']
                        # 兼容 camelCase(compositeScore) 和 snake_case(composite_score)
                        score_str = row.get('composite_score', '') or row.get('compositeScore', '')
                        new_score = float(score_str) if score_str else 0.0
                        confidence = row.get('confidence', 'MEDIUM')
                        if confidence not in ("HIGH", "MEDIUM"):
                            break
                        if new_dir != self.macro_direction:
                            self.macro_direction = new_dir
                            self.macro_score = new_score
                            self.write_log_safe(f"[MACRO] {self.symbol} direction updated: {self.macro_direction}, score: {self.macro_score:.2f}")
                        break
        except Exception as e:
            self.write_error(f"[ERROR] Failed to read macro signal: {e}")

    def on_tick(self, tick: TickData):
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        self.bg.update_bar(bar)

    def on_1min_bar(self, bar: BarData):
        # 优先使用事件驱动信号，fallback 到 CSV
        if not self._try_apply_event_signal():
            # 回测时传入bar时间，实盘时传入None
            self.load_macro_signal(bar.datetime)

        self.am.update_bar(bar)
        if not self.am.inited:
            return

        self.calc_tech_signal()
        self.check_entry(bar.close_price)
        self.check_exit(bar.close_price)

    def calc_tech_signal(self):
        fast_ma = self.am.sma(self.fast_window)
        slow_ma = self.am.sma(self.slow_window)

        fast_array = self.am.sma(self.fast_window, array=True)
        slow_array = self.am.sma(self.slow_window, array=True)
        
        # 确保有足够的数据
        if len(fast_array) < 2 or len(slow_array) < 2:
            self.tech_direction = "NEUTRAL"
            return
            
        prev_fast = fast_array[-2]
        prev_slow = slow_array[-2]

        if prev_fast <= prev_slow and fast_ma > slow_ma:
            self.tech_direction = "LONG"
            self.write_log_safe(f"[TECH] {self.symbol} Golden Cross, direction: LONG")
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            self.tech_direction = "SHORT"
            self.write_log_safe(f"[TECH] {self.symbol} Death Cross, direction: SHORT")
        else:
            self.tech_direction = "NEUTRAL"

    def check_entry(self, price: float):
        if self.pos != 0:
            return
        
        if not self.use_macro:
            # 不使用宏观信号时，纯技术交易
            if self.tech_direction == "LONG":
                self.buy(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Pure tech LONG, price: {price}")
            elif self.tech_direction == "SHORT":
                self.short(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Pure tech SHORT, price: {price}")
            return

        # 使用宏观信号过滤
        if self.macro_direction == "LONG":
            # 宏观看多：只允许开多单
            if self.tech_direction == "LONG":
                self.buy(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Macro LONG + Tech LONG, price: {price}")
        elif self.macro_direction == "SHORT":
            # 宏观看空：只允许开空单
            if self.tech_direction == "SHORT":
                self.short(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Macro SHORT + Tech SHORT, price: {price}")
        else:
            # 宏观中性：允许双向开仓（纯技术信号）
            if self.tech_direction == "LONG":
                self.buy(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Macro NEUTRAL + Tech LONG, price: {price}")
            elif self.tech_direction == "SHORT":
                self.short(price, 1)
                self.entry_price = price
                self.highest_price = price
                self.lowest_price = price
                self.write_log_safe(f"[ENTRY] Macro NEUTRAL + Tech SHORT, price: {price}")

    def check_exit(self, price: float):
        if self.pos == 0:
            return
        
        # 获取合约乘数
        size = self.symbol_config['size']
        
        # 更新持仓期间最高/最低价
        if self.pos > 0:
            self.highest_price = max(self.highest_price, price)
            
            # 固定止损检查（按金额计算）
            if self.enable_stop_loss:
                loss_per_lot = (self.entry_price - price) * size  # 每手亏损金额
                if loss_per_lot >= self.stop_loss:
                    self.sell(price, abs(self.pos))
                    self.write_log_safe(f"[STOP LOSS] LONG loss ¥{loss_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 固定止盈检查（按金额计算）
            if self.enable_take_profit:
                profit_per_lot = (price - self.entry_price) * size  # 每手盈利金额
                if profit_per_lot >= self.take_profit:
                    self.sell(price, abs(self.pos))
                    self.write_log_safe(f"[TAKE PROFIT] LONG profit ¥{profit_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 移动止损检查（按金额计算）
            if self.enable_trailing_stop:
                if self.highest_price > self.entry_price:
                    max_profit_per_lot = (self.highest_price - self.entry_price) * size  # 最大浮盈
                    current_profit_per_lot = (price - self.entry_price) * size  # 当前浮盈
                    pullback_per_lot = max_profit_per_lot - current_profit_per_lot  # 回撤金额
                    if pullback_per_lot >= self.trailing_stop:
                        self.sell(price, abs(self.pos))
                        self.write_log_safe(f"[TRAILING STOP] LONG pullback ¥{pullback_per_lot:.2f}/lot, close at {price}")
                        return
        
        elif self.pos < 0:
            self.lowest_price = min(self.lowest_price, price)
            
            # 固定止损检查（按金额计算）
            if self.enable_stop_loss:
                loss_per_lot = (price - self.entry_price) * size  # 每手亏损金额
                if loss_per_lot >= self.stop_loss:
                    self.cover(price, abs(self.pos))
                    self.write_log_safe(f"[STOP LOSS] SHORT loss ¥{loss_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 固定止盈检查（按金额计算）
            if self.enable_take_profit:
                profit_per_lot = (self.entry_price - price) * size  # 每手盈利金额
                if profit_per_lot >= self.take_profit:
                    self.cover(price, abs(self.pos))
                    self.write_log_safe(f"[TAKE PROFIT] SHORT profit ¥{profit_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 移动止损检查（按金额计算）
            if self.enable_trailing_stop:
                if self.lowest_price < self.entry_price:
                    max_profit_per_lot = (self.entry_price - self.lowest_price) * size  # 最大浮盈
                    current_profit_per_lot = (self.entry_price - price) * size  # 当前浮盈
                    pullback_per_lot = max_profit_per_lot - current_profit_per_lot  # 回撤金额
                    if pullback_per_lot >= self.trailing_stop:
                        self.cover(price, abs(self.pos))
                        self.write_log_safe(f"[TRAILING STOP] SHORT pullback ¥{pullback_per_lot:.2f}/lot, close at {price}")
                        return
        
        # 技术反转平仓（原有逻辑）
        if self.enable_tech_exit:
            if self.pos > 0 and self.tech_direction in ("SHORT", "NEUTRAL"):
                self.sell(price, abs(self.pos))
                self.write_log_safe(f"[EXIT] Tech reversal/neutral, close LONG, price: {price}")
            elif self.pos < 0 and self.tech_direction in ("LONG", "NEUTRAL"):
                self.cover(price, abs(self.pos))
                self.write_log_safe(f"[EXIT] Tech reversal/neutral, close SHORT, price: {price}")
