# 回测修复总结

## 修复时间
2026-04-25

## 问题描述
回测运行成功但没有产生任何交易，total_trade_count: 0

## 根本原因
存在**两个版本的策略文件**：
1. `D:\futures_v6\strategies\macro_demo_strategy.py`（新版本，支持回测日期）
2. `D:\futures_v6\macro_engine\strategies\macro_demo_strategy.py`（旧版本，只支持当前日期）

回测脚本将 `macro_engine` 目录插入到 `sys.path` 前面，导致 Python 优先加载旧版本策略。

## 修复步骤

### 1. 删除旧版本策略文件
```powershell
Remove-Item D:\futures_v6\macro_engine\strategies\macro_demo_strategy.py
```

### 2. 修复 macro_engine\strategies\__init__.py
移除对已删除文件的引用：
```python
# macro_engine strategies package
# Note: MacroDemoStrategy has been moved to futures_v6/strategies/
__all__ = []
```

### 3. 创建 strategies\__init__.py
```python
# strategies package
from .macro_demo_strategy import MacroDemoStrategy
__all__ = ["MacroDemoStrategy"]
```

### 4. 修正回测脚本路径顺序
移除 `macro_engine` 的路径插入，避免优先加载旧版本：
```python
# 删除以下代码
macro_dir = project_dir / 'macro_engine'
if str(macro_dir) not in sys.path:
    sys.path.insert(0, str(macro_dir))
```

### 5. 修正回测模式
使用正确的枚举值：
```python
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
# ...
mode=BacktestingMode.BAR  # 而不是 mode=1
```

### 6. 加载 BarData 而不是 TickData
回测引擎在 BAR_MODE 下期望 BarData 对象：
```python
bars = []
for _, row in df.iterrows():
    bar = BarData(
        symbol="RU2505",
        exchange=Exchange.SHFE,
        datetime=pd.to_datetime(row['datetime']),
        open_price=row['open'],
        high_price=row['high'],
        low_price=row['low'],
        close_price=row['close'],
        volume=row['volume'],
        open_interest=row['open_interest'],
        gateway_name="BACKTESTING"
    )
    bars.append(bar)
engine.history_data = bars
```

## 回测结果

修复后回测正常运行：
- **总成交次数**: 22
- **期末资金**: 1,000,415.54（盈利 415.54）
- **总净利润**: 415.54
- **总手续费**: 327.87
- **总滑点**: 440.00
- **总成交额**: 3,278,702.84
- **总收益率**: 0.04%
- **年化收益率**: 9.97%

## 关键教训

1. **避免代码重复**：不要在多个位置维护相同功能的代码
2. **注意 Python 路径优先级**：`sys.path` 中先出现的目录优先被搜索
3. **使用正确的枚举值**：`BacktestingMode.BAR` 而不是 `1`
4. **匹配数据类型**：BAR_MODE 下使用 BarData，TICK_MODE 下使用 TickData

## 后续优化建议

1. 添加更详细的交易日志记录
2. 优化策略参数（fast_window, slow_window）
3. 添加更多的技术指标组合
4. 实现止损止盈逻辑
