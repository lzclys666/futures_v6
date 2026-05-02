# VNpyBridge 测试报告

## 测试时间
2026-04-26

## 测试目标
验证VNpyBridge的核心功能:
1. 启动/停止VNpy引擎
2. 策略管理
3. 数据查询
4. 风控状态
5. 事件回调

## 测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 基本生命周期 | ❌ 失败 | EventEngine线程只能启动一次 |
| 策略管理 | ⚠️ 警告 | CTA引擎未初始化 |
| 数据查询 | ✅ 通过 | 返回空数据（未连接CTP） |
| 风控管理 | ✅ 通过 | 返回默认状态 |
| 事件回调 | ✅ 通过 | 回调触发正常 |

## 发现的问题

### 1. EventEngine线程只能启动一次
**错误信息**: `threads can only be started once`
**原因**: EventEngine使用了单例模式，其内部线程只能启动一次
**影响**: 无法重复启动/停止VNpy引擎
**解决方案**: 
- 方案A: 修改EventEngine为非单例模式
- 方案B: 在stop()中不停止EventEngine，只重置状态
- 方案C: 使用新的EventEngine实例（需要修改VNpy源码）

### 2. time模块冲突
**错误信息**: `TypeError: 'module' object is not callable`
**原因**: `import time` 覆盖了 `from datetime import time`
**状态**: ✅ 已修复

### 3. PaperAccount未安装
**错误信息**: `ModuleNotFoundError: No module named 'vnpy_paperaccount'`
**状态**: ✅ 已修复（添加try/except处理）

### 4. CTA引擎未初始化
**错误信息**: `CTA engine not initialized`
**原因**: 由于EventEngine启动失败，后续CTA引擎初始化也被跳过
**影响**: 策略管理功能无法使用

## 建议

1. **优先解决EventEngine单例问题** - 这是阻塞性问题
2. **安装vnpy_paperaccount** - 用于模拟交易测试
3. **补充策略类** - 需要MacroRiskStrategy类才能测试策略管理

## 下一步

1. 修复EventEngine启动问题
2. 重新运行完整测试
3. 补充策略加载测试
4. 测试CTP连接（需要实盘账户）
