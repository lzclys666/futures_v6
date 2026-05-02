import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import os
import sqlite3
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("IR < -0.5 失效品种处理方案")
print("=" * 80)

# 加载22品种参数分析结果
params_path = r'D:\futures_v6\macro_engine\research\reports\optimization\22_variety_params.csv'
params_df = pd.read_csv(params_path)

print("\n[1] 失效品种识别（IR < -0.5）")
print("-" * 80)

# 识别失效品种
failed_varieties = params_df[params_df['ir'] < -0.5].copy()
failed_varieties = failed_varieties.sort_values('ir')

print(f"\n发现 {len(failed_varieties)} 个失效品种：")
print(failed_varieties[['variety', 'ir', 'ic_mean', 'win_rate', 'ic_window', 'hold_period']].to_string(index=False))

# ============================================================
# 失效原因分析
# ============================================================

print("\n[2] 失效原因分析")
print("-" * 80)

failure_analysis = {
    'AU': {
        'name': '黄金',
        'ir': -2.01,
        'reason': '动量因子与黄金特性不匹配',
        'detail': '黄金作为避险资产，价格走势与风险资产相反。动量策略在趋势明显时有效，但黄金受地缘政治、货币政策影响大，经常出现反转',
        'suggestion': '改用反向因子（反转策略）或宏观因子（美元指数、实际利率）'
    },
    'M': {
        'name': '豆粕',
        'ir': -0.93,
        'reason': '农产品季节性影响',
        'detail': '豆粕受南美/北美种植周期影响，季节性极强。简单动量无法捕捉季节性规律',
        'suggestion': '引入季节性因子、天气因子、库存因子'
    },
    'SN': {
        'name': '锡',
        'ir': -0.53,
        'reason': '小品种流动性问题',
        'detail': '锡交易量小，价格容易被操纵，动量信号噪声大',
        'suggestion': '改用基本面因子（库存/产量）或降低权重'
    },
    'BR': {
        'name': '合成橡胶',
        'ir': -0.53,
        'reason': '与原油相关性复杂',
        'detail': '合成橡胶成本受原油影响，但传导有滞后，简单动量无法捕捉',
        'suggestion': '引入成本传导因子（原油→丁二烯→合成橡胶）'
    },
    'AO': {
        'name': '氧化铝',
        'ir': -0.52,
        'reason': '新品种数据不足',
        'detail': '氧化铝上市时间短，历史数据不足以支撑动量策略',
        'suggestion': '积累更多数据后再评估，或改用跨市场套利因子'
    }
}

for code, info in failure_analysis.items():
    print(f"\n【{code} - {info['name']}】")
    print(f"  IR: {info['ir']:.4f}")
    print(f"  失效原因: {info['reason']}")
    print(f"  详细分析: {info['detail']}")
    print(f"  处理建议: {info['suggestion']}")

# ============================================================
# 处理方案
# ============================================================

print("\n[3] 失效品种处理方案")
print("=" * 80)

class FailedVarietyHandler:
    """
    失效品种处理器
    提供多种处理策略
    """
    
    def __init__(self, params_df):
        self.params_df = params_df
        self.failed_varieties = params_df[params_df['ir'] < -0.5]['variety'].tolist()
        self.base_path = r'D:\futures_v6\macro_engine\data\crawlers'
    
    def strategy_1_reverse_signal(self, variety):
        """
        策略1: 反转信号
        IR为负说明因子方向错误，直接反转信号
        """
        row = self.params_df[self.params_df['variety'] == variety].iloc[0]
        
        return {
            'variety': variety,
            'strategy': 'reverse_signal',
            'description': '反转信号方向',
            'original_ir': row['ir'],
            'expected_ir': -row['ir'],
            'implementation': f"将{variety}的信号乘以-1",
            'risk': '可能加剧回撤，需小仓位测试'
        }
    
    def strategy_2_switch_factor(self, variety):
        """
        策略2: 切换因子
        从动量因子切换到其他因子
        """
        factor_mapping = {
            'AU': '美元指数/实际利率',
            'M': '季节性因子/库存因子',
            'SN': '库存/产量因子',
            'BR': '成本传导因子',
            'AO': '跨市场套利因子'
        }
        
        row = self.params_df[self.params_df['variety'] == variety].iloc[0]
        
        return {
            'variety': variety,
            'strategy': 'switch_factor',
            'description': '切换因子类型',
            'original_ir': row['ir'],
            'suggested_factor': factor_mapping.get(variety, '基本面因子'),
            'implementation': f"从动量因子切换到{factor_mapping.get(variety, '其他因子')}",
            'risk': '需要重新验证新因子的有效性'
        }
    
    def strategy_3_reduce_weight(self, variety):
        """
        策略3: 降低权重
        不删除品种，但降低其在组合中的权重
        """
        row = self.params_df[self.params_df['variety'] == variety].iloc[0]
        
        # 根据IR绝对值计算权重
        abs_ir = abs(row['ir'])
        if abs_ir > 1.0:
            weight = 0.0  # 完全剔除
        elif abs_ir > 0.5:
            weight = 0.2  # 降低至20%
        else:
            weight = 0.5  # 降低至50%
        
        return {
            'variety': variety,
            'strategy': 'reduce_weight',
            'description': '降低品种权重',
            'original_ir': row['ir'],
            'suggested_weight': weight,
            'implementation': f"将{variety}权重降至{weight:.0%}",
            'risk': '可能错过反弹机会'
        }
    
    def strategy_4_increase_hold(self, variety):
        """
        策略4: 延长持有期
        某些品种需要更长的持有期才能体现因子效果
        """
        row = self.params_df[self.params_df['variety'] == variety].iloc[0]
        
        return {
            'variety': variety,
            'strategy': 'increase_hold',
            'description': '延长持有期',
            'original_ir': row['ir'],
            'original_hold': int(row['hold_period']),
            'suggested_hold': int(row['hold_period']) * 2,
            'implementation': f"将持有期从{int(row['hold_period'])}日延长至{int(row['hold_period'])*2}日",
            'risk': '增加暴露时间，可能放大亏损'
        }
    
    def strategy_5_pause_trading(self, variety):
        """
        策略5: 暂停交易
        暂时停止该品种交易，等待因子恢复
        """
        row = self.params_df[self.params_df['variety'] == variety].iloc[0]
        
        return {
            'variety': variety,
            'strategy': 'pause_trading',
            'description': '暂停交易',
            'original_ir': row['ir'],
            'implementation': f"暂停{variety}交易，每月重新评估",
            'risk': '完全错过该品种机会'
        }
    
    def generate_handling_plan(self):
        """
        生成完整的失效品种处理方案
        """
        print("\n[3.1] 方案A: 反转信号（推荐用于IR -0.5 ~ -1.0）")
        print("-" * 80)
        
        plan_a = []
        for variety in self.failed_varieties:
            row = self.params_df[self.params_df['variety'] == variety].iloc[0]
            if -1.0 <= row['ir'] < -0.5:
                result = self.strategy_1_reverse_signal(variety)
                plan_a.append(result)
                print(f"\n{variety}: {result['description']}")
                print(f"  原IR: {result['original_ir']:.4f} → 预期IR: {result['expected_ir']:.4f}")
                print(f"  实施: {result['implementation']}")
        
        print("\n[3.2] 方案B: 切换因子（推荐用于IR < -1.0 或 基本面品种）")
        print("-" * 80)
        
        plan_b = []
        for variety in self.failed_varieties:
            row = self.params_df[self.params_df['variety'] == variety].iloc[0]
            if row['ir'] < -1.0 or variety in ['M', 'SN']:
                result = self.strategy_2_switch_factor(variety)
                plan_b.append(result)
                print(f"\n{variety}: {result['description']}")
                print(f"  建议因子: {result['suggested_factor']}")
                print(f"  实施: {result['implementation']}")
        
        print("\n[3.3] 方案C: 降低权重（通用方案）")
        print("-" * 80)
        
        plan_c = []
        for variety in self.failed_varieties:
            result = self.strategy_3_reduce_weight(variety)
            plan_c.append(result)
            print(f"\n{variety}: {result['description']}")
            print(f"  建议权重: {result['suggested_weight']:.0%}")
        
        print("\n[3.4] 方案D: 暂停交易（保守方案）")
        print("-" * 80)
        
        plan_d = []
        for variety in self.failed_varieties:
            result = self.strategy_5_pause_trading(variety)
            plan_d.append(result)
            print(f"\n{variety}: {result['description']}")
        
        return {
            'reverse_signal': plan_a,
            'switch_factor': plan_b,
            'reduce_weight': plan_c,
            'pause_trading': plan_d
        }

# 生成处理方案
handler = FailedVarietyHandler(params_df)
handling_plan = handler.generate_handling_plan()

# ============================================================
# 推荐方案
# ============================================================

print("\n[4] 推荐处理方案（综合策略）")
print("=" * 80)

recommendations = {
    'AU': {
        'action': 'switch_factor',
        'detail': '切换到美元指数/实际利率因子',
        'priority': 'P0',
        'timeline': '1周内'
    },
    'M': {
        'action': 'switch_factor',
        'detail': '引入季节性因子+库存因子',
        'priority': 'P1',
        'timeline': '2周内'
    },
    'SN': {
        'action': 'reduce_weight',
        'detail': '权重降至20%，同时研究基本面因子',
        'priority': 'P1',
        'timeline': '立即'
    },
    'BR': {
        'action': 'reverse_signal',
        'detail': '反转动量信号，测试效果',
        'priority': 'P2',
        'timeline': '1周内'
    },
    'AO': {
        'action': 'pause_trading',
        'detail': '暂停交易，积累数据后再评估',
        'priority': 'P2',
        'timeline': '立即'
    }
}

print("\n| 品种 | 行动 | 详情 | 优先级 | 时间线 |")
print("|------|------|------|--------|--------|")

for variety, rec in recommendations.items():
    name = failure_analysis[variety]['name']
    print(f"| {variety} ({name}) | {rec['action']} | {rec['detail']} | {rec['priority']} | {rec['timeline']} |")

# ============================================================
# 实施步骤
# ============================================================

print("\n[5] 实施步骤")
print("=" * 80)

implementation_steps = """
## 第一步：立即执行（今天）
1. 对SN、AO执行"降低权重"或"暂停交易"
2. 在参数数据库中标记这些品种为"失效"
3. 通知交易员这些品种信号不可靠

## 第二步：本周内
1. 对AU、M开发新因子
   - AU: 从AKShare获取美元指数、美债收益率数据
   - M: 从USDA获取种植进度、库存数据
2. 对BR测试反转信号
   - 修改信号生成逻辑：动量因子乘以-1
   - 回测验证反转后的效果

## 第三步：2周内
1. 新因子IC验证
   - 计算新因子的IC、IR、t统计量
   - 确保新因子IR > 0.3
2. 参数更新
   - 将新因子参数写入参数数据库
   - 更新日终打分任务

## 第四步：持续监控
1. 每周检查失效品种的IR变化
2. 如果IR回升至-0.5以上，考虑恢复交易
3. 如果IR持续恶化，考虑永久剔除
"""

print(implementation_steps)

# ============================================================
# 保存处理方案
# ============================================================

output_path = r'D:\futures_v6\macro_engine\research\reports\Failed_Variety_Handling_Plan_20260424.md'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("# IR < -0.5 失效品种处理方案\n\n")
    f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("## 1. 失效品种列表\n\n")
    f.write(failed_varieties[['variety', 'ir', 'ic_mean', 'win_rate']].to_markdown(index=False))
    f.write("\n\n## 2. 失效原因分析\n\n")
    
    for code, info in failure_analysis.items():
        f.write(f"### {code} - {info['name']}\n")
        f.write(f"- **IR**: {info['ir']:.4f}\n")
        f.write(f"- **失效原因**: {info['reason']}\n")
        f.write(f"- **详细分析**: {info['detail']}\n")
        f.write(f"- **处理建议**: {info['suggestion']}\n\n")
    
    f.write("## 3. 推荐处理方案\n\n")
    f.write("| 品种 | 行动 | 详情 | 优先级 | 时间线 |\n")
    f.write("|------|------|------|--------|--------|\n")
    for variety, rec in recommendations.items():
        name = failure_analysis[variety]['name']
        f.write(f"| {variety} ({name}) | {rec['action']} | {rec['detail']} | {rec['priority']} | {rec['timeline']} |\n")
    
    f.write("\n## 4. 实施步骤\n")
    f.write(implementation_steps)
    
    f.write("\n## 5. 监控指标\n\n")
    f.write("| 指标 | 正常范围 | 警告阈值 | 严重阈值 |\n")
    f.write("|------|----------|----------|----------|\n")
    f.write("| IR | > 0.3 | 0 ~ 0.3 | < 0 |\n")
    f.write("| 胜率 | > 55% | 50-55% | < 50% |\n")
    f.write("| 回撤 | < 10% | 10-20% | > 20% |\n")

print(f"\n[OK] 处理方案已保存: {output_path}")

print("\n" + "=" * 80)
print("失效品种处理方案生成完成！")
print("=" * 80)
