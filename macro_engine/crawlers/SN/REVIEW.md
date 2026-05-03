# SN（锡）因子采集脚本复查报告

**复查时间**: 2026-05-02 10:12 GMT+8  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\SN\`  
**复查人**: mimo (subagent)

---

## 1. 脚本清单

| 脚本 | 因子代码 | 状态 |
|------|---------|------|
| `SN_沪锡期货收盘价.py` | SN_FUT_CLOSE | ⛔ 无法运行 |
| `SN_沪锡期货持仓量.py` | SN_FUT_OI | ⛔ 无法运行 |
| `SN_沪锡期货库存.py` | SN_DCE_INV | ⛔ 无法运行 |
| `SN_run_all.py` | runner | ✅ 可运行 |

---

## 2. 逐脚本范式检查

### 2.1 SN_沪锡期货收盘价.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header，说明较完整 |
| try-except（禁止 bare except）| ✅ | `except Exception as e` |
| 网络超时设置 | ⚠️ | `akshare` 内部处理，无显式 timeout |
| 魔法数字常量 | ✅ | EMIN/EMAX 定义为常量 |
| 函数类型注解 | ❌ | `fetch()` 和 `main()` 无返回类型注解 |
| 日志记录 | ⚠️ | 有 print，无标准 logging |
| CSV 输出 | N/A | 数据直写 db，无 CSV |
| 无硬编码中文文件名 | ✅ | 写数据库，无此问题 |
| 中断/恢复逻辑 | ✅ | 有 L4 回补逻辑 |

**运行报错**:
```
NameError: name 'os' is not defined
```
缺失 `import os`，导致 `this_dir = os.path.dirname(...)` 报错。

---

### 2.2 SN_沪锡期货持仓量.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header |
| try-except（禁止 bare except）| ❌ | `except Exception as e` 外层OK，但内层 `except:` 存在 |
| 网络超时设置 | ❌ | 无 timeout |
| 魔法数字常量 | ✅ | EMIN/EMAX 定义 |
| 函数类型注解 | ❌ | 无类型注解 |
| 日志记录 | ⚠️ | DEBUG print，无标准 logging |
| CSV 输出 | N/A | 直写 db |
| 无硬编码中文文件名 | ✅ | 写数据库 |
| 中断/恢复逻辑 | ❌ | 无任何回补/兜底逻辑 |

**运行报错**:
```
NameError: name 'os' is not defined
```
缺失 `import os`，且脚本在顶层直接执行（无 `if __name__ == "__main__": main()`），导致 `save_to_db` 在模块 import 时就执行而非被调用时。

---

### 2.3 SN_沪锡期货库存.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ✅ | 有 Header |
| try-except（禁止 bare except）| ✅ | `except Exception as e` |
| 网络超时设置 | ❌ | 无 timeout |
| 魔法数字常量 | ✅ | EMIN/EMAX 定义 |
| 函数类型注解 | ❌ | 无类型注解 |
| 日志记录 | ⚠️ | 有 print，无标准 logging |
| CSV 输出 | N/A | 直写 db |
| 无硬编码中文文件名 | ✅ | 写数据库 |
| 中断/恢复逻辑 | ✅ | 有 L4 回补 |

**运行报错**:
```
NameError: name 'sys' is not defined
```
缺失 `import sys`，但 `sys.path.insert` 依赖它。

---

### 2.4 SN_run_all.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 头部 docstring | ❌ | 无 docstring |
| try-except（禁止 bare except）| ✅ | 外层 `except Exception as e`，内层 `except:` 存在 |
| 网络超时设置 | ✅ | `subprocess.run(..., timeout=30)` |
| 魔法数字常量 | ✅ | 魔法数字少，可接受 |
| 函数类型注解 | ❌ | `main()` 无注解 |
| 日志记录 | ⚠️ | print，无标准 logging |

---

## 3. 根因分析

三个因子脚本都因 **缺失标准库 import** 导致无法运行：

- `SN_沪锡期货收盘价.py` → 缺 `import os`
- `SN_沪锡期货持仓量.py` → 缺 `import os`
- `SN_沪锡期货库存.py` → 缺 `import sys`

**为什么会出现**：脚本在 `import` 行之前就开始使用模块（如 `sys.path.insert` 在文件第17行，但 `import sys` 不存在）。很可能是从其他脚本复制粘贴后遗漏了 import。

---

## 4. 运行日志

```
==================================================
SN @ 2026-05-02T10:12:15.159546
==================================================
>> SN_沪锡期货收盘价.py
>> SN_沪锡期货持仓量.py
>> SN_沪锡期货库存.py
==================================================
SN Done 0.1s OK=0/3
==================================================
```

0/3 成功，所有子脚本立即失败（0.1s 说明根本没跑到数据获取逻辑）。

---

## 5. README.md 更新内容

```markdown
# SN 锡期货因子数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `SN` |
| 中文名称 | 锡 |
| 交易所 | SHFE |
| 合约代码 | SN |
| 品种分类 | 有色金属 |
| 因子数量 | 3 |
| 数据库因子数 | 3 |

## 因子配置

- `SN_DCE_INV` — 沪锡期货库存
- `SN_FUT_CLOSE` — 沪锡期货收盘价
- `SN_FUT_OI` — 沪锡期货持仓量

## 脚本说明

总计：4 个脚本（working 0 / broken 3 / runner 1）

- `SN_沪锡期货收盘价.py` — ⛔ broken（缺 `import os`，NameError）
- `SN_沪锡期货持仓量.py` — ⛔ broken（缺 `import os`，NameError）
- `SN_沪锡期货库存.py` — ⛔ broken（缺 `import sys`，NameError）
- `SN_run_all.py` — ✅ working（runner 正常，但子脚本全挂）

## 运行方式

```bash
# 批量采集（推荐）
python crawlers/SN/SN_run_all.py --auto

# 单脚本调试
python crawlers/SN/<脚本名>.py --auto
```

## 状态栏

> ⚠️ 3 个因子脚本存在致命 import 错误，无法运行
> 根因：复制粘贴后遗漏标准库 import（os/sys）
> 修复：添加缺失的 import 语句

---
_更新时间: 2026-05-02 | 负责人: mimo_
```

---

## 6. 修复优先级

| 优先级 | 脚本 | 问题 | 预计工时 |
|--------|------|------|----------|
| P0 | `SN_沪锡期货收盘价.py` | +`import os` | 1 min |
| P0 | `SN_沪锡期货持仓量.py` | +`import os`，包装为 `main()` | 5 min |
| P0 | `SN_沪锡期货库存.py` | +`import sys` | 1 min |

所有脚本还需要补充：函数类型注解、统一用 `logging` 替代 print。
