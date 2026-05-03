# ZN（锌）因子采集脚本复查报告

**复查时间**: 2026-05-02 10:18 GMT+8  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\ZN\`  
**复查人**: 程序员mimo (subagent)

---

## 1. 脚本清单

| 脚本 | 因子代码 | 状态 |
|------|---------|------|
| `ZN_run_all.py` | — | ⛔ 运行失败 |
| `ZN_沪锌期货收盘价.py` | `ZN_FUT_CLOSE` | ⛔ 运行失败 |
| `ZN_沪锌期货持仓量.py` | `ZN_FUT_OI` | ⛔ 运行失败 |
| `ZN_沪锌期货库存.py` | `ZN_DCE_INV` | ⛔ 运行失败 |

---

## 2. 逐脚本范式检查

### 2.1 ZN_run_all.py

| 检查项 | 结果 | 详情 |
|--------|------|------|
| 头部 docstring | ⚠️ 缺失 | 无模块级 docstring |
| try-except（非 bare） | ❌ 有 bare except | 第 33 行 `except:` 无异常类型 |
| timeout 设置 | ✅ 有 | `subprocess.run(..., timeout=30)` |
| 魔法数字常量 | ✅ | SCRIPTS、timeout |
| 类型注解 | ❌ 缺失 | `main()` 无注解 |
| 日志记录 | ⚠️ 纯 print | 未使用 logging 模块 |
| 输出路径 | N/A | 无 CSV 输出，走 db_utils |
| 无硬编码中文文件名 | ✅ | — |
| 中断/恢复 | N/A | — |

**运行日志**:
```
==================================================
ZN @ 2026-05-02T10:18:49.540522
==================================================
>> ZN_沪锌期货收盘价.py
>> ZN_沪锌期货持仓量.py
>> ZN_沪锌期货库存.py
ZN Done 0.1s OK=0/3
==================================================
```
0.1s 完成说明 3 个子脚本全部在 import 阶段崩溃，未真正执行。

---

### 2.2 ZN_沪锌期货收盘价.py

| 检查项 | 结果 | 详情 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header，状态 ⚠️ 待修复 |
| try-except（非 bare） | ✅ | `except Exception as e` |
| timeout 设置 | ❌ 缺失 | AKShare 调用无 timeout |
| 魔法数字常量 | ✅ | EMIN=15000, EMAX=35000 |
| 类型注解 | ❌ 缺失 | `fetch()`, `main()` 无注解 |
| 日志记录 | ⚠️ 纯 print | 无 logging |
| 输出路径 | ✅ | db_utils → pit_data.db |
| 无硬编码中文文件名 | ✅ | — |
| 中断/恢复 | N/A | — |

**运行错误**:
```
NameError: name 'os' is not defined
  File "ZN_沪锌期货收盘价.py", line 17
    this_dir = os.path.dirname(os.path.abspath(__file__))
```

**致命缺陷**: `os` 模块未 import，但代码中使用了 `os.path.dirname` 和 `os.path.join`。

---

### 2.3 ZN_沪锌期货持仓量.py

| 检查项 | 结果 | 详情 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header，状态 ⚠️ 待修复 |
| try-except（非 bare） | ✅ | `except Exception as e` |
| timeout 设置 | ❌ 缺失 | AKShare 调用无 timeout |
| 魔法数字常量 | ✅ | EMIN=50000, EMAX=400000 |
| 类型注解 | ❌ 缺失 | `fetch()`, `main()` 无注解 |
| 日志记录 | ⚠️ 纯 print | 无 logging |
| 输出路径 | ✅ | db_utils → pit_data.db |
| 无硬编码中文文件名 | ✅ | — |
| 中断/恢复 | N/A | — |

**运行错误**:
```
NameError: name 'os' is not defined
  File "ZN_沪锌期货持仓量.py", line 17
    this_dir = os.path.dirname(os.path.abspath(__file__))
```

**致命缺陷**: `os` 模块未 import，但代码中使用了 `os.path.dirname` 和 `os.path.join`。

---

### 2.4 ZN_沪锌期货库存.py

| 检查项 | 结果 | 详情 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header，状态 ⚠️ 待修复 |
| try-except（非 bare） | ✅ | `except Exception as e` |
| timeout 设置 | ❌ 缺失 | AKShare 调用无 timeout |
| 魔法数字常量 | ✅ | EMIN=50000, EMAX=300000 |
| 类型注解 | ❌ 缺失 | `fetch()`, `main()` 无注解 |
| 日志记录 | ⚠️ 纯 print | 无 logging |
| 输出路径 | ✅ | db_utils → pit_data.db |
| 无硬编码中文文件名 | ✅ | — |
| 中断/恢复 | N/A | — |

**运行错误**:
```
NameError: name 'sys' is not defined
  File "ZN_沪锌期货库存.py", line 17
    sys.path.insert(0, 'd:/futures_v6/macro_engine/crawlers/common')
```

**致命缺陷**: `sys` 模块未 import，但代码中使用了 `sys.path.insert`。

---

## 3. 汇总问题

### 🔴 致命问题（脚本完全无法运行）

| # | 问题 | 影响脚本 |
|---|------|---------|
| 1 | `import os` 缺失 | 收盘价、持仓量 |
| 2 | `import sys` 缺失 | 库存 |

### 🟡 规范问题（运行后可能存在的问题）

| # | 问题 | 影响脚本 |
|---|------|---------|
| 1 | AKShare 调用无 timeout | 全部 3 个因子脚本 |
| 2 | 函数无类型注解 | 全部 3 个因子脚本 |
| 3 | bare except（`except:`） | ZN_run_all.py |
| 4 | 未使用 logging 模块（纯 print） | 全部 4 个脚本 |

---

## 4. 修复建议

### 4.1 ZN_沪锌期货库存.py
**第 17 行前添加**:
```python
import sys
```

### 4.2 ZN_沪锌期货收盘价.py / ZN_沪锌期货持仓量.py
**顶部 import 区域添加**:
```python
import os
```

### 4.3 ZN_run_all.py
将第 33 行 `except:` 改为 `except Exception:`。

---

## 5. README.md 更新内容

```markdown
# ZN（锌）期货基本面数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `ZN` |
| 中文名称 | 锌 |
| 交易所 | SHFE |
| 合约代码 | ZN |
| 品种分类 | 有色金属 |
| 因子数量 | 3 |
| 数据库因子数 | 3 |
| 数据库记录数 | 2807 |

## 数据来源

> AKShare / 交易所官网 / 付费源(Mysteel/汾渭/普氏)

## 因子配置

- `ZN_DCE_INV` — 沪锌期货库存
- `ZN_FUT_CLOSE` — 沪锌期货收盘价
- `ZN_FUT_OI` — 沪锌期货持仓量

## 脚本状态

共 4 个脚本（working 0 / stub 3 / broken 1）

| 脚本 | 状态 | 说明 |
|------|------|------|
| `ZN_run_all.py` | 🔴 broken | bare except，需修复 `except:` → `except Exception:` |
| `ZN_沪锌期货收盘价.py` | 🔴 broken | 缺 `import os`，脚本无法启动 |
| `ZN_沪锌期货持仓量.py` | 🔴 broken | 缺 `import os`，脚本无法启动 |
| `ZN_沪锌期货库存.py` | 🔴 broken | 缺 `import sys`，脚本无法启动 |

## 运行方式

```bash
# 批量采集（推荐）
python crawlers/ZN/ZN_run_all.py --auto

# 单脚本测试
python crawlers/ZN/<脚本名>.py --auto
```

## 状态备注

> 🔴 所有因子脚本均无法运行（import 缺失），需紧急修复后方可采集数据。

---
_更新时间: 2026-05-02 | 负责人: 程序员mimo_
```

---

## 6. 结论

**所有 4 个脚本均无法正常工作**，其中 3 个因子脚本因缺少 import 导致 `NameError` 立即崩溃，1 个 run_all 脚本有 bare except 语法规范问题。

优先修复：分别为 `ZN_沪锌期货库存.py` 添加 `import sys`，为 `ZN_沪锌期货收盘价.py` 和 `ZN_沪锌期货持仓量.py` 添加 `import os`，然后修复 `ZN_run_all.py` 的 bare except。
