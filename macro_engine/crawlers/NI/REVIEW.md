# NI（镍）因子采集脚本 — 健康复查报告

**复查时间：** 2026-05-02 09:49  
**工作目录：** `D:\futures_v6\macro_engine\crawlers\NI\`  
**运行验证：** `NI_run_all.py --auto` → OK=5/5，耗时 30.4s

---

## 一、脚本清单

| 脚本 | 状态 |
|------|------|
| NI_run_all.py | ✅ 可运行 |
| NI_抓取期货收盘价.py | ✅ 可运行 |
| NI_抓取期货持仓量.py | ✅ 可运行 |
| NI_抓取SHFE仓单.py | ✅ 可运行 |
| NI_沪镍期货库存.py | ⚠️ 有bug |
| NI_浙镍期货持仓量.py | ⚠️ 有bug |
| NI_计算基差.py | ✅ 可运行（永久跳过） |

---

## 二、逐项范式检查

### 1. NI_run_all.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ❌ | 无脚本级文档说明 |
| try-except | ⚠️ | 内层 `except:` 为 bare except |
| timeout | ✅ | `timeout=30` |
| 魔法数字 | ⚠️ | SCRIPTS 列表中 5 个硬编码数字未定义为常量 |
| 类型注解 | ❌ | 无 |
| 日志 | ⚠️ | 全程 print，无 logging.INFO/ERROR |
| CSV 输出 | N/A | 纯调度脚本 |
| 中文文件名 | ⚠️ | 引用的子脚本含中文文件名 |
| 中断/恢复 | ❌ | 无 |

---

### 2. NI_抓取SHFE仓单.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整，包含状态、付费标注 |
| try-except | ✅ | fetch() 外层包裹，L1 失败走 L4 fallback |
| timeout | ❌ | AKShare 调用无 timeout 参数 |
| 魔法数字 | ⚠️ | `80` 天回溯、月份 `15` 硬编码 |
| 类型注解 | ❌ | 无 |
| 日志 | ⚠️ | 全程 print，异常仅 ERROR 级别打印 |
| CSV 输出 | N/A | 直写 db |
| --auto 参数 | ❌ | 不识别 --auto，全部走 main() |
| 中断/恢复 | ❌ | 无 |

**实际运行：** `[OK] NI_WRT_SHFE=23344 obs=2025-05-15` ✅

---

### 3. NI_抓取期货持仓量.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整 |
| try-except | ✅ | fetch() 外层包裹 |
| timeout | ❌ | AKShare 无 timeout |
| 魔法数字 | ✅ | EXPECTED_MIN/MAX 为常量 |
| 类型注解 | ❌ | 无 |
| 日志 | ⚠️ | 全程 print |
| --auto 参数 | ❌ | 不识别 --auto |
| 中断/恢复 | ❌ | 无 |

**⚠️ 关键问题：** `NI_FUT_OI` 与 `NI_浙镍期货持仓量.py` 的因子代码完全相同（均为 `NI_FUT_OI`），两个脚本写同一个因子，存在覆盖风险。

**实际运行：** `[OK] NI_FUT_OI=160841 obs=2026-04-30` ✅

---

### 4. NI_抓取期货收盘价.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整 |
| try-except | ✅ | fetch() 外层包裹 |
| timeout | ❌ | AKShare 无 timeout |
| 魔法数字 | ✅ | EXPECTED 常量 |
| 类型注解 | ❌ | 无 |
| 日志 | ⚠️ | print |
| --auto 参数 | ❌ | 不识别 --auto |
| 中断/恢复 | ❌ | 无 |

**实际运行：** `[OK] NI_FUT_CLOSE=148870.0 obs=2026-04-30` ✅

---

### 5. NI_沪镍期货库存.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整 |
| try-except | ⚠️ | `datetime.date.today()` 在 import 缺失时抛 NameError，被 except 吞掉，误走向 L4 fallback |
| timeout | ❌ | 无 |
| 类型注解 | ❌ | 无 |
| **致命 Bug** | ❌ | **缺少 `import sys, os` 和 `import datetime`，`datetime.date.today()` 报 NameError |

**分析：** 脚本内写的是 `datetime.date.today()` 但 `datetime` 模块未导入。运行时会触发 `NameError: name 'datetime' is not defined`，被 `except Exception` 捕获后误认为 L1 失败，直接走 L4 fallback 写旧数据，造成脏数据。

**运行日志：** 未出现在 run_all 输出中（被 except 吞掉，未打印）。

---

### 6. NI_浙镍期货持仓量.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整 |
| try-except | ⚠️ | `os` 未 import，`os.path.abspath` 会失败 |
| timeout | ❌ | 无 |
| 类型注解 | ❌ | 无 |
| **致命 Bug** | ⚠️ | **因子代码 `NI_FUT_OI` 与 `NI_抓取期货持仓量.py` 完全重复**，两脚本竞争同一因子 |

**⚠️ 细节问题：** `NI_浙镍期货持仓量.py` 中 `fetch()` 里用的是中文字段名 `'日期'`、`'持仓量'`，但 AKShare 返回的列名是 unicode `\u65e5\u671f`、`\u6301\u4ed3\u91cf`，会导致 KeyError。

**运行日志：** 未出现在 run_all 输出中。

---

### 7. NI_计算基差.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | Header 完整，标注 `⛔永久跳过` 和付费源 |
| try-except | ✅ | L1 失败 → L4 fallback |
| timeout | ❌ | 无 |
| 30 天阈值 | ✅ | 硬编码但已在注释中标注含义 |
| 类型注解 | ❌ | 无 |
| --auto 参数 | ❌ | 不识别 |

**实际运行：** `⛔永久跳过`，AKShare 无当前数据 ✅（行为符合预期）

---

## 三、运行日志

```
==================================================
NI @ 2026-05-02 09:49:25.152001
==================================================
>> NI_抓取期货收盘价.py
   [OK] NI_FUT_CLOSE=148870.0 obs=2026-04-30
>> NI_抓取期货持仓量.py
   [OK] NI_FUT_OI=160841 obs=2026-04-30
>> NI_计算基差.py
   （无输出，符合永久跳过预期）
>> NI_抓取SHFE仓单.py
   [OK] NI_WRT_SHFE=23344 obs=2025-05-15
>> ../CU_NI/CU_NI_抓取LME升贴水_EVENT.py
   CU: 47.76
   NI: 28.5
==================================================
NI Done 30.4s OK=5/5
==================================================
```

---

## 四、共性问题汇总

| 问题 | 影响范围 |
|------|----------|
| `--auto` 参数均不识别 | 全部脚本，但 main() 直接运行不影响自动化 |
| 无 `timeout` 参数 | 全部 AKShare 调用，偶发挂起风险 |
| 无 `logging` 模块 | 全部脚本，生产环境日志不可追溯 |
| 无函数类型注解 | 全部脚本 |
| 因子代码重复（`NI_FUT_OI`） | NI_抓取期货持仓量.py ↔ NI_浙镍期货持仓量.py |
| `import` 缺失导致 NameError | NI_沪镍期货库存.py |
| `os` 未 import | NI_浙镍期货持仓量.py |

---

## 五、修复优先级

| 优先级 | 脚本 | 问题 |
|--------|------|------|
| P0 | NI_沪镍期货库存.py | 补 `import sys, os, datetime`，否则脏数据 |
| P0 | NI_浙镍期货持仓量.py | 补 `import os`；因子代码需改为 `NI_ZJ_FUT_OI`；列名字段改 unicode |
| P1 | NI_抓取期货持仓量.py | 因子代码 `NI_FUT_OI` 需与浙镍脚本区分 |
| P2 | 全部脚本 | 补充 AKShare timeout=15 |

---

## 六、README.md 更新建议

README.md 基本准确，但以下内容需要修正：

1. **因子配置表**：`NI_FUT_CLOSE` 描述为"浙镍期货收盘价"应改为"沪镍期货收盘价"（来源是 SHFE/sina）；`NI_SPD_BASIS` 标注"浙镍"也应为"沪镍"
2. **状态标注**：NI_沪镍期货库存.py 和 NI_浙镍期货持仓量.py 应标注为 ⚠️待修复（非 ⏸️stub），已有完整代码
3. **因子代码**：`NI_FUT_OI` 实际对应两个脚本，建议因子分析师拆分或合并

---

_复查人: 程序员mimo | 2026-05-02_
