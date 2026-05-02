# 因子系统API文档

## 1. 数据接口

### 1.1 加载因子数据
```python
from factor_system import FactorLoader

loader = FactorLoader()
factor = loader.load_factor('AG', '金银比')
```

### 1.2 加载价格数据
```python
price = loader.load_price('AG')
```

## 2. 计算接口

### 2.1 计算IC
```python
from factor_system import ICAnalyzer

analyzer = ICAnalyzer()
ic_series = analyzer.compute_ic(factor, price, window=60)
```

### 2.2 计算信号
```python
from factor_system import SignalScorer

scorer = SignalScorer()
signal = scorer.compute_signal(factor, price)
```

## 3. 报告接口

### 3.1 生成IC报告
```python
from factor_system import ReportGenerator

generator = ReportGenerator()
generator.generate_ic_report(variety='AG', factor='金银比')
```

### 3.2 生成信号报告
```python
generator.generate_signal_report(variety='AG')
```

## 4. 配置接口

### 4.1 获取配置
```python
from factor_system import Config

config = Config()
ic_window = config.get('ic_window', default=60)
```

### 4.2 设置配置
```python
config.set('ic_window', 80)
```

## 5. 错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|---------|
| 1001 | 数据不存在 | 检查数据路径 |
| 1002 | 计算错误 | 检查数据完整性 |
| 1003 | 配置错误 | 检查配置文件 |
| 2001 | 系统错误 | 联系运维人员 |
