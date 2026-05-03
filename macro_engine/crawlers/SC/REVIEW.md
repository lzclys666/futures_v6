# SC（原油）因子采集脚本复查报告

**复查时间**: 2026-05-02 10:10 GMT+8
**工作目录**: `D:\futures_v6\macro_engine\crawlers\SC\`
**复查人**: mimo

---

## 一、脚本清单

| 文件名 | 大小 | 最后修改 |
|--------|------|----------|
| `SC_run_all.py` | 1406 B | 2026/4/23 |
| `SC_原油期货收盘价.py` | 1701 B | 2026/5/2 |
| `SC_原油期货持仓量.py` | 1680 B | 2026/5/2 |

---

## 二、范式检查结果

### 2.1 SC_run_all.py — ⚠️ 有问题

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ❌ | 缺失，顶部只有 shebang 和 coding |
| try-except（无 bare except） | ⚠️ | 有 `except Exception` 也有 bare `except` |
| 网络超时设置 | ❌ | 无网络请求，是 subprocess 调用 |
| 魔法数字常量 | ⚠️ | `timeout=30` 内联，应为常量 |
| 类型注解 | ❌ | 函数无类型注解 |
| 日志级别（INFO/ERROR） | ⚠️ | 只有 print，无日志级别区分 |
| CSV 输出路径 | ❌ | 输出到数据库，不是 CSV |
| 无硬编码中文文件名 | ⚠️ | `SCRIPTS` 列表硬编码了中文文件名 |
| 中断/恢复逻辑 | ❌ | 无 |

### 2.2 SC_原油期货收盘价.py — ❌ 运行失败

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ⚠️ | 有但不规范（状态仍为"待定义"） |
| try-except | ✅ | 有 `except Exception` |
| 网络超时设置 | ✅ | AKShare 内部处理 |
| 魔法数字常量 | ⚠️ | EMIN/EMAX 已定义，其他数字内联 |
| 类型注解 | ❌ | 函数无类型注解 |
| 日志级别（INFO/ERROR） | ⚠️ | 只有 print，无 INFO/ERROR 级别 |
| CSV 输出路径 | ❌ | 输出到数据库，不是 CSV |
| 无硬编码中文文件名 | ❌ | 文件名含中文 |
| 中断/恢复逻辑 | ❌ | 无 |
| **Critical Bug** | ❌❌ | **`import os` 缺失，Line 17 `NameError: name 'os' is not defined`** |

### 2.3 SC_原油期货持仓量.py — ❌ 运行失败

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ⚠️ | 有但不规范（状态仍为"待定义"） |
| try-except | ✅ | 有 `except Exception` |
| 网络超时设置 | ✅ | AKShare 内部处理 |
| 魔法数字常量 | ⚠️ | EMIN/EMAX 已定义，其他数字内联 |
| 类型注解 | ❌ | 函数无类型注解 |
| 日志级别（INFO/ERROR） | ⚠️ | 只有 print，无 INFO/ERROR 级别 |
| CSV 输出路径 | ❌ | 输出到数据库，不是 CSV |
| 无硬编码中文文件名 | ❌ | 文件名含中文 |
| 中断/恢复逻辑 | ❌ | 无 |
| **Critical Bug** | ❌❌ | **`import os` 缺失，Line 17 `NameError: name 'os' is not defined`** |

---

## 三、运行验证

### 3.1 SC_run_all.py 执行结果

```
==================================================
SC @ 2026-05-02T10:10:20.724988
==================================================
>> SC_ԭ���ڻ����̼�.py
>> SC_ԭ���ڻ��ֲ���.py
==================================================
SC Done 0.1s OK=0/2
==================================================
```

**结果**: 0/2 通过，子进程均失败。

### 3.2 单脚本执行结果

**SC_原油期货收盘价.py:**
```
NameError: name 'os' is not defined
  File "D:\futures_v6\macro_engine\crawlers\SC\SC_原油期货收盘价.py", line 17, in <module>
    this_dir = os.path.dirname(os.path.abspath(__file__))
```

**SC_原油期货持仓量.py:**
```
NameError: name 'os' is not defined
  File "D:\futures_v6\macro_engine\crawlers\SC\SC_原油期货持仓量.py", line 17, in <module>
    this_dir = os.path.dirname(os.path.abspath(__file__))
```

---

## 四、关键 Bug 分析

### 4.1 致命 Bug: `import os` 缺失

两个因子脚本在 `this_dir = os.path.dirname(...)` 之前都没有 `import os`，导致脚本启动即崩溃。

**根因**: 脚本从 docstring 后直接跳到了 `this_dir = ...`，`import os` 语句（在标准 Python 中应紧跟 shebang/coding）被放在了 `this_dir` 之后，但 `this_dir` 本身已经依赖 `os` 模块。

**修复方案**: 在 `this_dir = ...` 之前插入 `import os`。

---

## 五、README.md 更新

### 当前 README.md 存在的问题

- 标记为 "stub" 状态，但脚本已有 fetch/main 逻辑，应更新为"⚠️待修复"
- 缺少对实际 Bug 的说明

### 建议更新内容

```markdown
# SC — 原油 期货数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `SC` |
| 中文名称 | 原油 |
| 交易所 | INE |
| 合约代码 | SC |
| 品种分类 | 能化 |
| 因子数量 | 2 |
| 数据库因子数 | 2 |
| 数据库记录数 | 3190 |

## 数据源

> AKShare / 付费源(Mysteel/汾渭/隆众)

## 因子配置

- `SC_FUT_CLOSE` — 原油期货收盘价
- `SC_FUT_OI` — 原油期货持仓量

## 爬虫脚本

总计：3 个脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `SC_run_all.py` | ✅ 可运行 | 入口脚本，调度两个因子脚本 |
| `SC_原油期货收盘价.py` | ❌ 运行失败 | **Bug**: `import os` 缺失，Line 17 NameError |
| `SC_原油期货持仓量.py` | ❌ 运行失败 | **Bug**: `import os` 缺失，Line 17 NameError |

## 运行方式

```bash
# 批量采集（推荐）
python crawlers/SC/SC_run_all.py --auto

# 单脚本测试
python crawlers/SC/<脚本名>.py --auto
```

## 已知问题

> ⚠️ 2026-05-02: 两个因子脚本均存在 `import os` 缺失 Bug，修复前无法正常运行。

---

_最后更新时间: 2026-05-02 | 复查人: mimo_
```

---

## 六、总结

| 项目 | 结果 |
|------|------|
| 脚本总数 | 3 |
| 可正常运行 | 0 |
| 致命 Bug | 2 (`import os` 缺失) |
| 范式达标 | 0 |
| 需优先修复 | `import os` 缺失 |

**下一步行动**: 修复 `import os` 缺失问题后重新验证采集逻辑。
