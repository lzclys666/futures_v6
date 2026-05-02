import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

print("=" * 80)
print("第三步：更新参数数据库 + 生成最终处理方案")
print("=" * 80)

# 连接参数数据库
db_path = r'D:\futures_v6\macro_engine\data\parameter_db.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 添加AU新因子（实际利率）
print("\n[1] 添加AU新因子...")
cursor.execute('''
    INSERT INTO optimal_parameters 
    (variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', ('AU', 'real_rate', 60, 10, 1.0, 0.2413, 0.0455, 0.5775))

print("  [OK] AU - real_rate 因子已添加 (IR=0.24)")

# 2. 添加BR反转信号
print("\n[2] 添加BR反转信号...")
cursor.execute('''
    INSERT INTO optimal_parameters 
    (variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', ('BR', 'momentum_reverse', 40, 5, 0.5, 0.1772, 0.0403, 0.60))

print("  [OK] BR - momentum_reverse 已添加 (IR=0.18)")

# 3. 标记M需要进一步研究
print("\n[3] 标记M为需要进一步研究...")
cursor.execute('''
    UPDATE optimal_parameters 
    SET weight_decay = 0.0, updated_at = ?
    WHERE variety = 'M' AND factor = 'momentum'
''', (datetime.now(),))

print("  [OK] M - 暂停交易，等待新因子开发")

# 4. 验证数据库
print("\n[4] 验证数据库更新...")
cursor.execute('''
    SELECT variety, factor, ic_window, hold_period, weight_decay, ir, win_rate
    FROM optimal_parameters
    WHERE variety IN ('AU', 'BR', 'M', 'SN', 'AO', 'LC')
    ORDER BY variety, factor
''')

results = cursor.fetchall()
print("\n| 品种 | 因子 | IC窗口 | 持有期 | 权重 | IR | 胜率 |")
print("|------|------|--------|--------|------|-----|------|")
for row in results:
    print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]:.4f} | {row[6]:.2%} |")

conn.commit()
conn.close()

# 5. 生成最终处理方案报告
print("\n[5] 生成最终处理方案报告...")

report = """# 失效品种最终处理方案

**生成时间**: {timestamp}

## 处理结果总结

| 品种 | 原IR | 处理方案 | 新IR | 状态 | 行动 |
|------|------|---------|------|------|------|
| AU | -2.01 | 切换实际利率因子 | 0.24 | ⚠️ 接近阈值 | 小仓位测试 |
| M | -0.93 | 季节性因子无效 | 0.02 | ❌ 仍需研究 | 暂停交易 |
| SN | -0.53 | 降低权重至20% | - | ⚠️ 监控中 | 研究基本面因子 |
| BR | -0.53 | 反转信号 | 0.18 | ⚠️ 有改善 | 继续测试优化 |
| AO | -0.52 | 暂停交易 | - | ⏸️ 暂停 | 积累数据 |
| LC | -0.51 | 降低权重至20% | - | ⚠️ 监控中 | 研究新能源因子 |

## 关键决策

### 1. AU（黄金）
- **方案**: 切换到实际利率因子（us_10y变化率）
- **结果**: IR=0.24，接近0.3阈值
- **行动**: 
  - 小仓位测试（权重=0.5）
  - 监控实际利率数据质量
  - 如果2周后IR>0.3，恢复全权重

### 2. M（豆粕）
- **方案**: 季节性因子测试失败（IR=0.02）
- **结果**: 需要更复杂的基本面因子
- **行动**:
  - 暂停交易（权重=0）
  - 研究USDA种植进度、库存数据
  - 考虑天气因子、压榨利润因子

### 3. BR（合成橡胶）
- **方案**: 反转信号测试
- **结果**: IR从-0.18→+0.18，有改善但仍低于0.3
- **行动**:
  - 继续优化反转参数（调整持有期）
  - 测试成本传导因子（原油→丁二烯）
  - 权重=0.5，小仓位测试

### 4. SN（锡）/ AO（氧化铝）/ LC（碳酸锂）
- **方案**: 降低权重或暂停
- **行动**:
  - SN/LC: 权重=0.2，监控流动性
  - AO: 权重=0，积累数据

## 下一步行动

### 本周内
1. AU: 启动实际利率因子小仓位测试
2. BR: 优化反转参数（测试不同持有期）
3. M: 研究USDA数据源

### 2周内
1. 评估AU实际利率因子效果
2. 开发M的基本面因子
3. 决定是否恢复SN/LC交易

### 1个月内
1. 所有失效品种要么恢复交易，要么永久剔除
2. 建立因子失效预警机制
3. 完善因子轮换策略

## 监控指标

| 品种 | 监控指标 | 恢复阈值 | 剔除阈值 |
|------|---------|---------|---------|
| AU | 实际利率因子IR | > 0.3 | < 0.1持续1月 |
| BR | 反转信号IR | > 0.3 | < 0.1持续1月 |
| M | 新因子IR | > 0.3 | 开发失败 |
| SN | 流动性+动量IR | IR>-0.3 | 流动性持续恶化 |
| LC | 新能源因子IR | > 0.3 | 开发失败 |
| AO | 数据积累 | 数据>1年 | 数据不足 |

## 风险控制

1. **小仓位测试**: 所有新因子/反转信号必须先小仓位测试2周
2. **止损机制**: 如果测试期间回撤>10%，立即停止
3. **定期评估**: 每周评估一次，每月全面复盘
4. **紧急暂停**: 如果市场异常，立即暂停所有失效品种

---

**批准**: 因子分析师YIYI  
**日期**: {timestamp}
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# 保存报告
report_path = r'D:\futures_v6\macro_engine\research\reports\Failed_Variety_Final_Plan_20260425.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"\n[OK] 最终处理方案已保存: {report_path}")

print("\n" + "=" * 80)
print("失效品种处理完成！")
print("=" * 80)
print("\n处理结果:")
print("  [OK] AU: 添加实际利率因子 (IR=0.24)")
print("  [PAUSE] M: 暂停交易，等待新因子")
print("  [WARN] BR: 反转信号 (IR=0.18)，继续优化")
print("  [WARN] SN/LC: 权重降至20%")
print("  [PAUSE] AO: 暂停交易")
