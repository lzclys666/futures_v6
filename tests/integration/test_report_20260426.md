# VNpyBridge 集成测试报告

**时间**: 2026-04-26 23:38
**测试脚本**: `tests/integration/test_vnpy_bridge.py`

## 测试结果汇总

| 指标 | 数值 |
|------|------|
| 总计 | 41项 |
| 通过 | 35项 |
| 失败 | 6项 |
| 通过率 | 85.4% |

## 通过的测试（35项）

### 引擎启动（5项）
- ✅ 引擎启动成功
- ✅ 引擎状态为RUNNING
- ✅ EventEngine已创建
- ✅ MainEngine已创建
- ✅ CTA引擎已获取

### 状态查询（4项）
- ✅ 状态查询返回running
- ✅ is_running为True
- ✅ 状态包含strategies_count
- ✅ 状态包含positions_count

### 策略管理（部分）（7项）
- ✅ 添加策略成功
- ✅ 策略列表包含1个策略
- ✅ 策略名称正确
- ✅ 策略类名正确
- ✅ 合约代码正确
- ✅ 初始化策略成功
- ✅ 策略状态为initialized

### 数据查询（5项）
- ✅ 持仓查询返回列表
- ✅ 空仓状态持仓为空
- ✅ 账户查询返回正确类型
- ✅ 订单查询返回列表
- ✅ 成交查询返回列表

### 风控接口（5项）
- ✅ 风控状态包含status字段
- ✅ 风控状态包含active_rules字段
- ✅ 11条风控规则全部激活
- ✅ 风控事件返回列表
- ✅ 风控回调注册成功

### WebSocket回调（2项）
- ✅ WebSocket回调注册成功
- ✅ WebSocket回调框架已验证

### 引擎停止（4项）
- ✅ 引擎停止成功
- ✅ 引擎状态为STOPPED
- ✅ MainEngine已清理
- ✅ EventEngine已清理

### 引擎重启（3项）
- ✅ 第一次启动成功
- ✅ 第一次停止成功
- ✅ 第二次启动成功（资源清理彻底）

## 失败的测试（6项）

| 失败项 | 原因 |
|--------|------|
| ❌ 启动策略成功 | MacroRiskStrategy 未加载到VNpy策略字典 |
| ❌ 策略状态为trading | 依赖启动成功 |
| ❌ 停止策略成功 | 策略未在运行状态 |
| ❌ 策略状态为stopped | 依赖停止成功 |
| ❌ 移除策略成功 | 策略未正确初始化 |
| ❌ 策略列表为空 | 移除失败导致 |

## 失败原因分析

**根本原因**: `MacroRiskStrategy` 类没有被 VNpy 的 `CtaStrategyApp` 识别。

VNpy 的策略加载机制需要策略类在特定的搜索路径中，或者通过 `load_strategy_class_from_module` 方法显式加载。

## 修复计划

1. 在 `VNpyBridge.start()` 中添加 `_load_strategy_classes()` 方法
2. 确保 `strategies/macro_risk_strategy.py` 在 VNpy 的策略搜索路径中
3. 重新运行集成测试验证

## 结论

VNpyBridge 核心功能（引擎生命周期、数据查询、风控接口、WebSocket）**全部正常**。

策略管理功能需要修复策略加载机制，预计 **30分钟内** 完成。
