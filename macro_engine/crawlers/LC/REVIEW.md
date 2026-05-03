# LC 因子采集脚本复查报告

**复查时间**: 2026-05-02 09:42
**工作目录**: `D:\futures_v6\macro_engine\crawlers\LC\`
**检查人**: mimo (subagent)

---

## 一、脚本清单

| 文件名 | 大小 | 最后修改 |
|--------|------|----------|
| `LC_run_all.py` | 1412 | 2026/4/23 12:30 |
| `LC_碳酸锂期货收盘价.py` | 1712 | 2026/5/2 7:46 |
| `LC_碳酸锂期货持仓量.py` | 1686 | 2026/5/2 7:46 |
| `README.md` | 1026 | 2026/5/2 9:19 |

---

## 二、各脚本检查结果

### 1. LC_run_all.py ⚠️ 基本可用（有瑕疵）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ⚠️ | 无显式 docstring，隐式通过 print 自我介绍 |
| try-except | ✅ | `subprocess.run` 包裹在 try-except 中 |
| timeout | ✅ | `timeout=30` |
| 魔法数字常量 | ❌ | `30`, `80`, `120` 硬编码在函数体内 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | print 输出，INFO 级别 |
| CSV 输出路径 | N/A | 调用子脚本，无直接 CSV 输出 |
| 无硬编码中文文件名 | ✅ | |
| 中断/恢复逻辑 | ❌ | 无 |

### 2. LC_碳酸锂期货收盘价.py ❌ 致命错误（无法运行）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ✅ | 符合 Header 规范 |
| try-except | ✅ | 独立 try-except（非 bare except） |
| timeout | ⚠️ | akshare 接口无显式 timeout（框架限制） |
| 魔法数字常量 | ✅ | `EMIN=50000`, `EMAX=300000` |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | INFO/ERROR 级别标记清晰 |
| CSV 输出路径 | N/A | 输出到 `save_to_db` → `pit_data.db`（非 CSV） |
| 无硬编码中文文件名 | ✅ | |
| 中断/恢复逻辑 | ⚠️ | L4 兜底有 fallback 逻辑 |

**🚨 致命 Bug**: 缺少 `import os` 和 `import sys`，导致运行时 `NameError: name 'os' is not defined`。

```python
# 实际文件第 17-18 行（AST 分析确认）:
this_dir = os.path.dirname(os.path.abspath(__file__))  # os 未导入！
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))  # sys 未导入！
```

**实际运行的 import 语句**（AST 确认）：
- `from db_utils import save_to_db, get_latest_value`
- `import akshare as ak`
- `from datetime import date`
- `import pandas as pd`

缺少: `import os`, `import sys`

### 3. LC_碳酸锂期货持仓量.py ❌ 致命错误（无法运行）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部 docstring | ✅ | 符合 Header 规范 |
| try-except | ✅ | 独立 try-except（非 bare except） |
| timeout | ⚠️ | akshare 接口无显式 timeout（框架限制） |
| 魔法数字常量 | ✅ | `EMIN=10000`, `EMAX=500000` |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | INFO/ERROR 级别标记清晰 |
| CSV 输出路径 | N/A | 输出到 `save_to_db` → `pit_data.db`（非 CSV） |
| 无硬编码中文文件名 | ✅ | |
| 中断/恢复逻辑 | ⚠️ | L4 兜底有 fallback 逻辑 |

**🚨 致命 Bug**: 同上，缺少 `import os` 和 `import sys`。

---

## 三、运行验证

### 入口脚本运行

```
$ python LC_run_all.py --auto
==================================================
LC @ 2026-05-02T09:42:31.155510
==================================================
>> LC_̼����ڻ����̼�.py
>> LC_̼����ڻ��ֲ���.py
==================================================
LC Done 0.1s OK=0/2
==================================================
```

**结果**: 0/2 子脚本成功（两个都失败）

### 直接运行子脚本

```
$ python LC_碳酸锂期货收盘价.py --auto
Traceback (most recent call last):
  File "...\LC_碳酸锂期货收盘价.py", line 17, in <module>
    this_dir = os.path.dirname(os.path.abspath(__file__))
               ^^
NameError: name 'os' is not defined
```

### 数据库状态

```
LC records: 2662
('LC_FUT_CLOSE', 1333)
('LC_FUT_OI', 1329)
```

**结论**: 数据库中有历史数据（2662条），说明脚本曾经正常运行过。但当前脚本已损坏（缺少 import 语句）。

---

## 四、问题汇总

### 致命问题（阻塞）

1. **两个子脚本缺少 `import os` 和 `import sys`**
   - 导致 `NameError`，脚本完全无法运行
   - 这不是 AKShare 或数据源问题，是代码本身的问题
   - 原因：docstring 后的 import 语句缩进变成了 docstring 的一部分（AST 确认）

### 规范问题

1. **无类型注解** — 所有函数都缺少 type hints
2. **LC_run_all.py 魔法数字** — `30`, `80`, `120` 应定义为常量
3. **CSV 输出规范** — 范式要求输出到 `output\` 目录，但实际写到 `pit_data.db`（需确认规范是否已更新）

### 正面发现

1. Header 规范基本符合（状态 ⚠️待修复 符合实际状态）
2. 四层漏斗有实现（L1 fetch → L4 fallback）
3. 日志标记规范：`[OK]`, `[WARN]`, `[L1]`, `[L4]` 等

---

## 五、修复建议

### 必须修复（致命）

在 `LC_碳酸锂期货收盘价.py` 和 `LC_碳酸锂期货持仓量.py` 的 docstring 之后、第一次使用 `os`/`sys` 之前，添加：

```python
import os
import sys
```

### 建议修复（规范）

1. 为所有函数添加 type hints
2. 将 `LC_run_all.py` 中的魔法数字定义为常量
3. 确认 CSV 输出规范（db vs file）

---

_复查完成_
