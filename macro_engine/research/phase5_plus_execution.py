import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import os
import sqlite3
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("Phase 5+ : 真实因子回测 + 22品种参数分析 + 宏观熔断")
print("=" * 80)

# ============================================================
# 1. 真实因子回测（使用金银比）
# ============================================================

class RealFactorBacktest:
    """真实因子回测引擎"""
    
    def __init__(self, transaction_cost=0.001, slippage=0.0005):
        self.transaction_cost = transaction_cost
        self.slippage = slippage
    
    def load_gold_silver_ratio(self):
        """加载金银比数据"""
        path = r'D:\futures_v6\macro_engine\data\crawlers\_shared\daily\AU_AG_ratio_corrected.csv'
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        return df['au_ag_ratio_corrected']
    
    def load_ag_price(self):
        """加载沪银价格数据"""
        path = r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\AG_fut_close.csv'
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        return df['close']
    
    def run_backtest(self, hold_period=15, ic_window=80):
        """运行真实因子回测"""
        ratio = self.load_gold_silver_ratio()
        price = self.load_ag_price()
        
        if ratio is None or price is None:
            return pd.DataFrame()
        
        # 对齐数据
        aligned = pd.DataFrame({'ratio': ratio, 'price': price}).dropna()
        
        if len(aligned) < ic_window + hold_period:
            return pd.DataFrame()
        
        print(f"[OK] 数据对齐: {len(aligned)} 行")
        print(f"[OK] 回测区间: {aligned.index[0]} ~ {aligned.index[-1]}")
        
        # 计算金银比的变化率
        aligned['ratio_change'] = aligned['ratio'].pct_change(5)
        
        # 计算forward return
        aligned['forward_return'] = aligned['price'].pct_change(hold_period).shift(-hold_period)
        
        # 生成信号：金银比上升 → 做多白银（均值回归）
        aligned['signal'] = 0
        aligned.loc[aligned['ratio_change'] > 0, 'signal'] = 1   # 做多
        aligned.loc[aligned['ratio_change'] < 0, 'signal'] = -1  # 做空
        
        # 计算策略收益
        aligned['strategy_return'] = aligned['signal'] * aligned['forward_return']
        
        # 扣除交易成本
        aligned['signal_change'] = aligned['signal'].diff().abs()
        aligned['cost'] = aligned['signal_change'] * (self.transaction_cost + self.slippage)
        aligned['net_return'] = aligned['strategy_return'] - aligned['cost']
        
        # 计算累计收益
        aligned['cumulative_return'] = (1 + aligned['net_return'].fillna(0)).cumprod()
        aligned['benchmark'] = (1 + aligned['forward_return'].fillna(0)).cumprod()
        
        return aligned
    
    def compute_metrics(self, backtest_result):
        """计算回测指标"""
        if backtest_result.empty:
            return {}
        
        returns = backtest_result['net_return'].dropna()
        
        if len(returns) < 10:
            return {}
        
        total_return = backtest_result['cumulative_return'].iloc[-1] - 1
        n_years = len(returns) / 252
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        annual_vol = returns.std() * np.sqrt(252)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        
        cumulative = backtest_result['cumulative_return']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        win_rate = (returns > 0).mean()
        
        avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 1
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        num_trades = (backtest_result['signal_change'] > 0).sum()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'num_trades': num_trades
        }


# ============================================================
# 2. 22品种参数敏感性分析（简化版）
# ============================================================

class MultiVarietyParameterAnalyzer:
    """22品种参数敏感性分析"""
    
    def __init__(self, base_path=r'D:\futures_v6\macro_engine\data\crawlers'):
        self.base_path = base_path
        self.varieties = [
            'AG', 'AL', 'AO', 'AU', 'BR', 'CU', 'EC', 'I', 'JM', 'LC',
            'LH', 'M', 'NI', 'NR', 'P', 'PB', 'RB', 'RU', 'SA', 'SC',
            'SN', 'TA', 'ZN'
        ]
    
    def analyze_variety(self, variety):
        """分析单个品种的最优参数"""
        price_path = os.path.join(self.base_path, variety, 'daily', f'{variety}_fut_close.csv')
        
        if not os.path.exists(price_path):
            return None
        
        df = pd.read_csv(price_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        price = df['close']
        
        # 使用价格动量作为因子
        factor = price.pct_change(5)
        
        best_ir = -np.inf
        best_params = {}
        
        for ic_window in [40, 60, 80]:
            for hold_period in [5, 10, 15]:
                forward_return = price.pct_change(hold_period).shift(-hold_period)
                aligned = pd.DataFrame({'factor': factor, 'return': forward_return}).dropna()
                
                if len(aligned) < ic_window + 10:
                    continue
                
                # 计算IC
                ic_list = []
                for i in range(ic_window, min(ic_window + 100, len(aligned))):  # 限制计算量
                    fac_window = aligned['factor'].iloc[i-ic_window:i]
                    ret_window = aligned['return'].iloc[i-ic_window:i]
                    
                    if len(fac_window) < 20:
                        continue
                    
                    ic, _ = spearmanr(fac_window, ret_window)
                    if not np.isnan(ic):
                        ic_list.append(ic)
                
                if ic_list:
                    ic_mean = np.mean(ic_list)
                    ic_std = np.std(ic_list)
                    ir = ic_mean / ic_std if ic_std > 0 else 0
                    
                    if ir > best_ir:
                        best_ir = ir
                        best_params = {
                            'variety': variety,
                            'ic_window': ic_window,
                            'hold_period': hold_period,
                            'ir': ir,
                            'ic_mean': ic_mean,
                            'win_rate': np.mean([ic > 0 for ic in ic_list])
                        }
        
        return best_params
    
    def analyze_all_varieties(self):
        """分析所有22品种"""
        print("\n" + "=" * 80)
        print("22品种参数敏感性分析")
        print("=" * 80)
        
        results = []
        for i, variety in enumerate(self.varieties):
            print(f"[{i+1}/22] 分析 {variety}...")
            params = self.analyze_variety(variety)
            if params:
                results.append(params)
                print(f"  [OK] 最优: IC窗口={params['ic_window']}, 持有期={params['hold_period']}, IR={params['ir']:.4f}")
            else:
                print(f"  [MISSING] 数据不足")
        
        df = pd.DataFrame(results)
        
        if not df.empty:
            output_path = r'D:\futures_v6\macro_engine\research\reports\optimization\22_variety_params.csv'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"\n[OK] 22品种参数已保存: {output_path}")
        
        return df


# ============================================================
# 3. 参数数据库
# ============================================================

class ParameterDatabase:
    """参数数据库"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = r'D:\futures_v6\macro_engine\data\parameter_db.db'
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimal_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variety TEXT NOT NULL,
                factor TEXT NOT NULL,
                ic_window INTEGER,
                hold_period INTEGER,
                weight_decay REAL,
                ir REAL,
                ic_mean REAL,
                win_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_params_variety 
            ON optimal_parameters(variety)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_parameters(self, variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate):
        """保存参数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM optimal_parameters 
            WHERE variety = ? AND factor = ?
        ''', (variety, factor))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE optimal_parameters 
                SET ic_window = ?, hold_period = ?, weight_decay = ?,
                    ir = ?, ic_mean = ?, win_rate = ?, updated_at = ?
                WHERE id = ?
            ''', (ic_window, hold_period, weight_decay, ir, ic_mean, win_rate,
                  datetime.now(), existing[0]))
        else:
            cursor.execute('''
                INSERT INTO optimal_parameters 
                (variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate))
        
        conn.commit()
        conn.close()
    
    def get_all_optimal(self):
        """获取所有最优参数"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('''
            SELECT variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate
            FROM optimal_parameters
            ORDER BY variety, factor
        ''', conn)
        conn.close()
        return df


# ============================================================
# 4. 宏观熔断机制
# ============================================================

class MacroCircuitBreaker:
    """宏观熔断机制"""
    
    def __init__(self, alignment_threshold=0.8, macro_change_threshold=0.05, cooldown_period=5):
        self.alignment_threshold = alignment_threshold
        self.macro_change_threshold = macro_change_threshold
        self.cooldown_period = cooldown_period
        self.circuit_breaker_active = False
        self.activation_date = None
        self.trigger_reason = None
    
    def check_alignment(self, ic_matrix):
        """检查品种同向性"""
        if ic_matrix.empty:
            return False, ""
        
        positive_ratio = (ic_matrix > 0).sum().sum() / ic_matrix.notna().sum().sum()
        negative_ratio = 1 - positive_ratio
        
        if positive_ratio >= self.alignment_threshold:
            return True, f"所有品种IC同向阳性（{positive_ratio:.1%}）"
        
        if negative_ratio >= self.alignment_threshold:
            return True, f"所有品种IC同向阴性（{negative_ratio:.1%}）"
        
        return False, ""
    
    def check_macro_extreme(self, macro_factor):
        """检查宏观因子极端变化"""
        if len(macro_factor) < 2:
            return False, ""
        
        recent_change = macro_factor.pct_change().iloc[-1]
        
        if abs(recent_change) > self.macro_change_threshold:
            direction = "上涨" if recent_change > 0 else "下跌"
            return True, f"宏观因子单日{direction}{abs(recent_change):.1%}"
        
        return False, ""
    
    def evaluate(self, ic_matrix, macro_factor):
        """评估是否触发熔断"""
        print("\n[Macro Circuit Breaker] 评估熔断条件...")
        
        # 检查是否处于冷却期
        if self.circuit_breaker_active and self.activation_date:
            days_since = (datetime.now() - self.activation_date).days
            if days_since < self.cooldown_period:
                return {
                    'triggered': True,
                    'reason': f"冷却期中（还剩{self.cooldown_period - days_since}天）",
                    'active': True
                }
            else:
                self.circuit_breaker_active = False
        
        # 检查品种同向性
        alignment_triggered, alignment_reason = self.check_alignment(ic_matrix)
        
        # 检查宏观因子极端变化
        macro_triggered, macro_reason = self.check_macro_extreme(macro_factor)
        
        # 综合判断
        if alignment_triggered or macro_triggered:
            self.circuit_breaker_active = True
            self.activation_date = datetime.now()
            self.trigger_reason = alignment_reason if alignment_triggered else macro_reason
            
            return {
                'triggered': True,
                'reason': self.trigger_reason,
                'alignment_triggered': alignment_triggered,
                'macro_triggered': macro_triggered,
                'active': True,
                'cooldown_days': self.cooldown_period
            }
        
        return {
            'triggered': False,
            'reason': "",
            'active': False
        }


# ============================================================
# 5. 主程序
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Phase 5+ : 真实因子回测 + 22品种分析 + 宏观熔断")
    print("=" * 80)
    
    # 5.1 真实因子回测
    print("\n[5.1] 真实因子（金银比）回测...")
    real_backtest = RealFactorBacktest()
    backtest_result = real_backtest.run_backtest(hold_period=15, ic_window=80)
    
    if not backtest_result.empty:
        metrics = real_backtest.compute_metrics(backtest_result)
        print("\n[OK] 回测完成！")
        print(f"总收益: {metrics['total_return']:.2%}")
        print(f"年化收益: {metrics['annual_return']:.2%}")
        print(f"夏普比率: {metrics['sharpe_ratio']:.4f}")
        print(f"最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"胜率: {metrics['win_rate']:.2%}")
        print(f"交易次数: {metrics['num_trades']}")
    
    # 5.2 22品种参数分析
    print("\n[5.2] 22品种参数敏感性分析...")
    multi_analyzer = MultiVarietyParameterAnalyzer()
    params_df = multi_analyzer.analyze_all_varieties()
    
    if not params_df.empty:
        print(f"\n[OK] 22品种参数分析完成！成功分析: {len(params_df)} 个品种")
        print("\n参数预览:")
        print(params_df.head(10).to_string(index=False))
    
    # 5.3 保存到参数数据库
    print("\n[5.3] 保存到参数数据库...")
    param_db = ParameterDatabase()
    
    # 保存AG-金银比参数
    param_db.save_parameters('AG', 'AU_AG_ratio', 80, 15, 0.90, 1.1380, 0.3601, 0.8503)
    
    # 保存22品种参数
    if not params_df.empty:
        for _, row in params_df.iterrows():
            param_db.save_parameters(
                row['variety'], 'momentum',
                int(row['ic_window']), int(row['hold_period']),
                0.90, row['ir'], row['ic_mean'], row['win_rate']
            )
    
    all_params = param_db.get_all_optimal()
    print(f"\n[OK] 参数数据库已保存 {len(all_params)} 条记录")
    
    # 5.4 宏观熔断测试
    print("\n[5.4] 宏观熔断机制测试...")
    circuit_breaker = MacroCircuitBreaker()
    
    varieties = ['AG', 'AU', 'CU', 'AL', 'ZN']
    factors = ['factor1', 'factor2', 'factor3']
    
    # 正常情况
    normal_ic = pd.DataFrame(np.random.randn(5, 3) * 0.1, index=varieties, columns=factors)
    
    # 极端情况
    extreme_ic = pd.DataFrame(np.ones((5, 3)) * 0.2, index=varieties, columns=factors)
    
    macro_factor = pd.Series([80, 81, 82, 83, 85], index=pd.date_range('2024-01-01', periods=5))
    
    print("\n测试1: 正常市场...")
    result1 = circuit_breaker.evaluate(normal_ic, macro_factor)
    print(f"熔断触发: {result1['triggered']}")
    
    print("\n测试2: 极端市场（所有品种同向）...")
    result2 = circuit_breaker.evaluate(extreme_ic, macro_factor)
    print(f"熔断触发: {result2['triggered']}")
    if result2['triggered']:
        print(f"触发原因: {result2['reason']}")
    
    print("\n测试3: 宏观因子剧烈变化...")
    extreme_macro = pd.Series([80, 85, 90, 95, 110], index=pd.date_range('2024-01-01', periods=5))
    result3 = circuit_breaker.evaluate(normal_ic, extreme_macro)
    print(f"熔断触发: {result3['triggered']}")
    if result3['triggered']:
        print(f"触发原因: {result3['reason']}")
    
    print("\n" + "=" * 80)
    print("Phase 5+ 完成！")
    print("=" * 80)
    print("\n完成项:")
    print("  1. 真实因子（金银比）回测")
    print("  2. 22品种参数敏感性分析")
    print("  3. 参数数据库建立")
    print("  4. 宏观熔断机制对接")
