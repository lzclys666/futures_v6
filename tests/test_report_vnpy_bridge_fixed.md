# VNpyBridge 测试报告（修复后）

## 测试时间
2026-04-26 13:56

## 修复内容

### 1. EventEngine线程重复启动问题 ✅
**问题**: `RuntimeError: threads can only be started once`
**根因**: MainEngine内部会调用event_engine.start()，如果外部先调用了一次，就会重复启动
**修复**: 创建EventEngine后不立即启动，让MainEngine来启动它
```python
# 修复前
self.event_engine = EventEngine()
self.event_engine.start()  # ❌ 重复启动
self.main_engine = MainEngine(self.event_engine)

# 修复后
self.event_engine = EventEngine()  # ✅ 只创建，不启动
self.main_engine = MainEngine(self.event_engine)  # MainEngine内部启动
```

### 2. time模块冲突 ✅
**问题**: `TypeError: 'module' object is not callable`
**修复**: `import time` 改为 `import time as time_module`，避免覆盖datetime.time

### 3. PaperAccount未安装 ✅
**修复**: 添加try/except处理，未安装时跳过

## 测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 基本生命周期 | ✅ 通过 | 启动/停止正常 |
| 策略管理 | ✅ 通过 | 添加/初始化策略正常 |
| 数据查询 | ✅ 通过 | 返回空数据（未连接CTP） |
| 风控管理 | ✅ 通过 | 返回11条活跃规则 |
| 事件回调 | ✅ 通过 | 回调触发正常 |

**总计: 5/5 通过**

## 日志输出
```
2026-04-26 13:55:58,175 - VNpyBridge - INFO - VNpy engine started successfully
2026-04-26 13:55:58,175 - VNpyBridge - INFO - Strategy added: test_ru (MacroRiskStrategy)
2026-04-26 13:55:58,175 - VNpyBridge - INFO - Strategy initialized: test_ru
```

## 待办事项
1. 安装vnpy_paperaccount进行模拟交易测试
2. 测试CTP连接（需要实盘账户）
3. 测试策略启动/停止循环
4. 测试WebSocket事件推送
