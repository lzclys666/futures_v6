# strategies/macro_risk_strategy.py
# -*- coding: utf-8 -*-
"""
宏观CTA策略 - 集成风控引擎版本
基于 MacroDemoStrategy，增加 RiskEngine 风控检查
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.constant import Direction, Offset, Status
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator, ArrayManager

from core.risk.risk_engine import RiskEngine, RiskContext, OrderRequest, RiskAction


# 品种配置映射表
SYMBOL_CONFIG = {
    'RU': {'exchange': 'SHFE', 'name': '天然橡胶', 'size': 10, 'pricetick': 5},
    'ZN': {'exchange': 'SHFE', 'name': '沪锌', 'size': 5, 'pricetick': 5},
    'RB': {'exchange': 'SHFE', 'name': '螺纹钢', 'size': 10, 'pricetick': 1},
    'NI': {'exchange': 'SHFE', 'name': '沪镍', 'size': 1, 'pricetick': 10},
    'CU': {'exchange': 'SHFE', 'name': '沪铜', 'size': 5, 'pricetick': 10},
    'AL': {'exchange': 'SHFE', 'name': '沪铝', 'size': 5, 'pricetick': 5},
    'AU': {'exchange': 'SHFE', 'name': '黄金', 'size': 1000, 'pricetick': 0.02},
    'AG': {'exchange': 'SHFE', 'name': '白银', 'size': 15, 'pricetick': 1},
    'I': {'exchange': 'DCE', 'name': '铁矿石', 'size': 100, 'pricetick': 0.5},
    'J': {'exchange': 'DCE', 'name': '焦炭', 'size': 100, 'pricetick': 0.5},
    'JM': {'exchange': 'DCE', 'name': '焦煤', 'size': 60, 'pricetick': 0.5},
    'M': {'exchange': 'DCE', 'name': '豆粕', 'size': 10, 'pricetick': 1},
    'Y': {'exchange': 'DCE', 'name': '豆油', 'size': 10, 'pricetick': 2},
    'P': {'exchange': 'DCE', 'name': '棕榈油', 'size': 10, 'pricetick': 2},
    'TA': {'exchange': 'CZCE', 'name': 'PTA', 'size': 5, 'pricetick': 2},
    'MA': {'exchange': 'CZCE', 'name': '甲醇', 'size': 10, 'pricetick': 1},
    'SR': {'exchange': 'CZCE', 'name': '白糖', 'size': 10, 'pricetick': 1},
    'CF': {'exchange': 'CZCE', 'name': '棉花', 'size': 5, 'pricetick': 5},
    'SC': {'exchange': 'INE', 'name': '原油', 'size': 1000, 'pricetick': 0.1},
    'NR': {'exchange': 'INE', 'name': '20号胶', 'size': 10, 'pricetick': 5},
}


class MacroRiskStrategy(CtaTemplate):
    """
    宏观CTA策略 - 集成风控引擎
    
    特性：
    1. 读取CSV宏观信号
    2. 技术指标共振确认
    3. 三层风控检查（Layer 1/2/3）
    4. 支持 Paper Trade / 实盘
    """

    author = "程序员deep"

    # 策略参数
    fast_window = 10
    slow_window = 20
    use_macro = True
    csv_path_str = "D:/futures_v6/macro_engine/output/{symbol}_macro_daily_{date}.csv"
    
    # 风控开关（原有）
    enable_stop_loss = True
    enable_take_profit = True
    enable_trailing_stop = True
    enable_tech_exit = True
    
    # 风控参数（原有）
    stop_loss = 5000
    take_profit = 10000
    trailing_stop = 3000
    
    # 新增：风控引擎配置
    risk_profile = "moderate"  # conservative/moderate/aggressive
    enable_risk_engine = True  # 总开关

    parameters = [
        "fast_window", "slow_window", "use_macro", "csv_path_str",
        "enable_stop_loss", "enable_take_profit", "enable_trailing_stop", "enable_tech_exit",
        "stop_loss", "take_profit", "trailing_stop",
        "risk_profile", "enable_risk_engine"
    ]
    variables = [
        "macro_direction", "macro_score", "tech_direction", 
        "entry_price", "highest_price", "lowest_price",
        "risk_status"  # 新增：风控状态
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.vt_symbol = vt_symbol
        self.symbol = self.extract_symbol(vt_symbol)
        self.symbol_config = self.get_symbol_config(self.symbol)
        
        # 宏观信号
        self.macro_direction = "NEUTRAL"
        self.macro_score = 50.0
        
        # 技术信号
        self.tech_direction = "NEUTRAL"
        self.bg = BarGenerator(self.on_bar, 1, self.on_1min_bar)
        self.am = ArrayManager()
        
        # 持仓管理
        self.entry_price = 0.0
        self.highest_price = 0.0
        self.lowest_price = 0.0
        
        # 风控引擎
        self.risk_engine = None
        self.risk_status = "OK"
        self._csv_missing_warned = False
        
        # 交易统计（用于R7连续亏损计算）
        self.trade_history = []

    def extract_symbol(self, vt_symbol: str) -> str:
        """从vt_symbol提取品种代码"""
        base = vt_symbol.split('.')[0]
        symbol = ''.join([c for c in base if not c.isdigit()]).upper()
        return symbol
    
    def get_symbol_config(self, symbol: str) -> dict:
        """获取品种配置"""
        config = SYMBOL_CONFIG.get(symbol)
        if config is None:
            self.write_log_safe(f"[WARNING] Unknown symbol: {symbol}, using default config")
            config = {'exchange': 'UNKNOWN', 'name': symbol, 'size': 10, 'pricetick': 1}
        return config
    
    def write_log_safe(self, msg: str):
        """安全写入日志"""
        if self.cta_engine is None:
            print(f"[LOG] {msg}")
            return
        try:
            self.write_log(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode('utf-8').decode('utf-8')
                self.write_log(safe_msg)
            except:
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                self.write_log(safe_msg)

    def on_init(self):
        """策略初始化"""
        self.write_log_safe(f"[INIT] MacroRiskStrategy init, symbol: {self.vt_symbol}")
        self.write_log_safe(f"[INIT] Risk profile: {self.risk_profile}")
        
        # 初始化风控引擎
        if self.enable_risk_engine:
            self.risk_engine = RiskEngine(profile=self.risk_profile)
            self.write_log_safe(f"[INIT] RiskEngine initialized with profile: {self.risk_profile}")
            self.write_log_safe(f"[INIT] Active rules: {[r.rule_id for r in self.risk_engine.rules if r.is_enabled()]}")
        
        self.load_macro_signal()

    def on_start(self):
        """策略启动"""
        self.write_log_safe("[START] Strategy started")

    def on_stop(self):
        """策略停止"""
        self.write_log_safe("[STOP] Strategy stopped")

    def on_timer(self):
        """定时器回调"""
        self.load_macro_signal()

    def load_macro_signal(self, bar_datetime=None):
        """加载宏观信号"""
        if bar_datetime is not None:
            date_str = bar_datetime.strftime("%Y%m%d")
        else:
            date_str = datetime.now().strftime("%Y%m%d")
        
        csv_path_str = self.csv_path_str.format(symbol=self.symbol, date=date_str)
        csv_path = os.path.normpath(csv_path_str)
        
        if not os.path.exists(csv_path):
            if bar_datetime is None and not self._csv_missing_warned:
                self.write_log_safe(f"[WARNING] CSV file not found: {csv_path}")
                self._csv_missing_warned = True
            return

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_type = row.get('row_type', '') or row.get('rowType', '')
                    row_symbol = row.get('symbol', '') or row.get('\ufeffsymbol', '')
                    if row_type == 'SUMMARY' and row_symbol == self.symbol:
                        new_dir = row['direction']
                        score_str = row.get('composite_score', '') or row.get('compositeScore', '')
                        new_score = float(score_str) if score_str else 0.0
                        confidence = row.get('confidence', 'MEDIUM')
                        if confidence not in ("HIGH", "MEDIUM"):
                            break
                        if new_dir != self.macro_direction:
                            self.macro_direction = new_dir
                            self.macro_score = new_score
                            self.write_log_safe(f"[MACRO] {self.symbol} direction: {self.macro_direction}, score: {self.macro_score:.2f}")
                        break
        except Exception as e:
            self.write_log_safe(f"[ERROR] Failed to read macro signal: {e}")

    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """Bar数据回调"""
        self.bg.update_bar(bar)

    def on_1min_bar(self, bar: BarData):
        """1分钟Bar回调 - 主交易逻辑"""
        # 加载宏观信号
        self.load_macro_signal(bar.datetime)
        
        # 更新技术指标
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算技术信号
        self.calc_tech_signal()
        
        # 检查入场
        self.check_entry(bar.close_price)
        
        # 检查出场（原有风控逻辑）
        self.check_exit(bar.close_price)

    def calc_tech_signal(self):
        """计算技术信号"""
        fast_ma = self.am.sma(self.fast_window)
        slow_ma = self.am.sma(self.slow_window)

        fast_array = self.am.sma(self.fast_window, array=True)
        slow_array = self.am.sma(self.slow_window, array=True)
        
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

    def check_risk(self, direction: str, offset: str, price: float, volume: int) -> bool:
        """
        风控检查
        
        Returns:
            bool: True if can trade, False otherwise
        """
        if not self.enable_risk_engine or self.risk_engine is None:
            return True
        
        # 构建订单请求
        exchange = self.symbol_config.get('exchange', 'SHFE')
        order = OrderRequest(
            symbol=self.symbol,
            exchange=exchange,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume
        )
        
        # 构建风控上下文
        context = self.build_risk_context(price)
        
        # 执行风控检查
        results = self.risk_engine.check_order(order, context)
        
        # 记录结果
        blocked = False
        warnings = []
        for result in results:
            if result.action == RiskAction.BLOCK:
                blocked = True
                self.write_log_safe(f"[RISK BLOCK] {result.rule_id}: {result.message}")
            elif result.action == RiskAction.WARN:
                warnings.append(result)
                self.write_log_safe(f"[RISK WARN] {result.rule_id}: {result.message}")
        
        if blocked:
            self.risk_status = f"BLOCKED by {results[-1].rule_id}"
            return False
        
        self.risk_status = "OK"
        return True

    def build_risk_context(self, price: float) -> RiskContext:
        """构建风控上下文"""
        # 获取账户信息
        account = {}
        if self.cta_engine and hasattr(self.cta_engine, 'engine'):
            # 尝试从引擎获取账户信息
            try:
                account_data = self.cta_engine.engine.get_account()
                if account_data:
                    account = {
                        'equity': getattr(account_data, 'balance', 100000),
                        'available': getattr(account_data, 'available', 80000),
                        'used_margin': getattr(account_data, 'margin', 15000),
                        'frozen': getattr(account_data, 'frozen', 0),
                        'pre_frozen': 0,
                        'daily_pnl': getattr(account_data, 'close_pnl', 0) + getattr(account_data, 'position_pnl', 0),
                    }
            except:
                pass
        
        if not account:
            # 使用默认值（Paper Trade模式）
            account = {
                'equity': 100000,
                'available': 80000,
                'used_margin': 15000,
                'frozen': 0,
                'pre_frozen': 0,
                'daily_pnl': 0,
            }
        
        # 获取持仓信息
        positions = {}
        if self.pos != 0:
            positions[self.symbol] = self.pos
        
        # 获取市场数据
        market_data = {
            'macro_score': self.macro_score,
            f'{self.symbol}_price': price,
            f'{self.symbol}_cost_price': self.entry_price if self.entry_price > 0 else price,
        }
        
        # 添加ATR数据（如果有）
        if self.am.inited:
            atr = self.am.atr(14)
            if atr > 0:
                market_data[f'{self.symbol}_atr_14'] = atr
        
        return RiskContext(
            account=account,
            positions=positions,
            market_data=market_data
        )

    def check_entry(self, price: float):
        """检查入场条件"""
        if self.pos != 0:
            return
        
        # 确定交易方向
        trade_direction = None
        
        if not self.use_macro:
            # 纯技术交易
            trade_direction = self.tech_direction
        else:
            # 宏观+技术共振
            if self.macro_direction == "LONG" and self.tech_direction == "LONG":
                trade_direction = "LONG"
            elif self.macro_direction == "SHORT" and self.tech_direction == "SHORT":
                trade_direction = "SHORT"
            elif self.macro_direction == "NEUTRAL":
                trade_direction = self.tech_direction
        
        if trade_direction not in ("LONG", "SHORT"):
            return
        
        # 风控检查
        if not self.check_risk(trade_direction, "OPEN", price, 1):
            return
        
        # 执行交易
        if trade_direction == "LONG":
            self.buy(price, 1)
            self.entry_price = price
            self.highest_price = price
            self.lowest_price = price
            self.write_log_safe(f"[ENTRY] LONG at {price} (Macro: {self.macro_direction}, Tech: {self.tech_direction})")
        else:
            self.short(price, 1)
            self.entry_price = price
            self.highest_price = price
            self.lowest_price = price
            self.write_log_safe(f"[ENTRY] SHORT at {price} (Macro: {self.macro_direction}, Tech: {self.tech_direction})")

    def check_exit(self, price: float):
        """检查出场条件（原有逻辑）"""
        if self.pos == 0:
            return
        
        size = self.symbol_config['size']
        
        if self.pos > 0:
            self.highest_price = max(self.highest_price, price)
            
            # 固定止损
            if self.enable_stop_loss:
                loss_per_lot = (self.entry_price - price) * size
                if loss_per_lot >= self.stop_loss:
                    self.sell(price, abs(self.pos))
                    self.write_log_safe(f"[STOP LOSS] LONG loss ¥{loss_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 固定止盈
            if self.enable_take_profit:
                profit_per_lot = (price - self.entry_price) * size
                if profit_per_lot >= self.take_profit:
                    self.sell(price, abs(self.pos))
                    self.write_log_safe(f"[TAKE PROFIT] LONG profit ¥{profit_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 移动止损
            if self.enable_trailing_stop:
                if self.highest_price > self.entry_price:
                    max_profit = (self.highest_price - self.entry_price) * size
                    current_profit = (price - self.entry_price) * size
                    pullback = max_profit - current_profit
                    if pullback >= self.trailing_stop:
                        self.sell(price, abs(self.pos))
                        self.write_log_safe(f"[TRAILING STOP] LONG pullback ¥{pullback:.2f}/lot, close at {price}")
                        return
            
            # 技术反转
            if self.enable_tech_exit and self.tech_direction in ("SHORT", "NEUTRAL"):
                self.sell(price, abs(self.pos))
                self.write_log_safe(f"[EXIT] Tech reversal, close LONG at {price}")
        
        elif self.pos < 0:
            self.lowest_price = min(self.lowest_price, price)
            
            # 固定止损
            if self.enable_stop_loss:
                loss_per_lot = (price - self.entry_price) * size
                if loss_per_lot >= self.stop_loss:
                    self.cover(price, abs(self.pos))
                    self.write_log_safe(f"[STOP LOSS] SHORT loss ¥{loss_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 固定止盈
            if self.enable_take_profit:
                profit_per_lot = (self.entry_price - price) * size
                if profit_per_lot >= self.take_profit:
                    self.cover(price, abs(self.pos))
                    self.write_log_safe(f"[TAKE PROFIT] SHORT profit ¥{profit_per_lot:.2f}/lot, close at {price}")
                    return
            
            # 移动止损
            if self.enable_trailing_stop:
                if self.lowest_price < self.entry_price:
                    max_profit = (self.entry_price - self.lowest_price) * size
                    current_profit = (self.entry_price - price) * size
                    pullback = max_profit - current_profit
                    if pullback >= self.trailing_stop:
                        self.cover(price, abs(self.pos))
                        self.write_log_safe(f"[TRAILING STOP] SHORT pullback ¥{pullback:.2f}/lot, close at {price}")
                        return
            
            # 技术反转
            if self.enable_tech_exit and self.tech_direction in ("LONG", "NEUTRAL"):
                self.cover(price, abs(self.pos))
                self.write_log_safe(f"[EXIT] Tech reversal, close SHORT at {price}")

    def on_trade(self, trade):
        """成交回调"""
        super().on_trade(trade)
        
        # 记录交易历史（用于R7连续亏损计算）
        pnl = getattr(trade, 'pnl', 0)
        self.trade_history.append({
            'time': trade.datetime,
            'direction': trade.direction.value,
            'price': trade.price,
            'volume': trade.volume,
            'pnl': pnl
        })
        
        # 更新R7规则状态
        if self.risk_engine and hasattr(self.risk_engine, 'rule_instances'):
            r7 = self.risk_engine.rule_instances.get('R7')
            if r7 and hasattr(r7, 'update_trade_result'):
                r7.update_trade_result(pnl)
                self.write_log_safe(f"[TRADE] PnL: {pnl:.2f}, Consecutive losses: {r7.consecutive_losses}")
        
        self.write_log_safe(f"[TRADE] {trade.direction.value} {trade.volume}@{trade.price}")


# ==================== 测试 ====================
if __name__ == "__main__":
    print("="*60)
    print("MacroRiskStrategy Test")
    print("="*60)
    
    # 创建策略实例（测试模式）
    strategy = MacroRiskStrategy(None, "test", "RU2505.SHFE", {})
    strategy.on_init()  # 手动调用初始化
    
    print(f"\nStrategy: {strategy.symbol}")
    print(f"Risk Profile: {strategy.risk_profile}")
    print(f"Risk Engine: {strategy.risk_engine is not None}")
    
    if strategy.risk_engine:
        print(f"Active Rules: {[r.rule_id for r in strategy.risk_engine.rules if r.is_enabled()]}")
    
    print("\nTest completed")
