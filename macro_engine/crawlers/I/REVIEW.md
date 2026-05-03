# I（铁矿石）因子采集脚本复查报告

复查时间：2026-05-02 09:45
复查人：mimo
工作目录：`D:\futures_v6\macro_engine\crawlers\I\`

---

## 一、脚本清单与范式检查

| # | 脚本名 | 因子代码 | 范式 | 主要问题 |
|---|--------|----------|------|----------|
| 1 | `I_run_all.py` | — | ⚠️有问题 | 无超时/重试/类型注解/日志 |
| 2 | `I_抓取期货收盘价.py` | `I_FUT_MAIN` | ⚠️有问题 | 无类型注解/无logging/无timeout |
| 3 | `I_抓取期货持仓量.py` | `I_FUT_OI` | ⚠️有问题 | 同上 |
| 4 | `I_抓取港口库存.py` | `I_STK_PORT` | ⚠️有问题 | 同上 |
| 5 | `I_计算基差.py` | `I_SPD_BASIS` | ⚠️有问题 | 同上 |
| 6 | `I_计算近远月价差.py` | `I_SPD_CONTRACT` | 🔴严重 | L4兜底只print不写DB |
| 7 | `I_批次2_手动输入.py` | BATCH2 | ✅可接受 | 仅打印说明，无实际采集 |

---

## 二、逐脚本详细分析

### 1. `I_run_all.py` — 总调度脚本

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有功能说明 |
| try-except | ⚠️ | run_script无保护，subprocess失败静默 |
| 网络超时 | ⚠️ | subprocess.run无timeout参数 |
| 魔法数字常量 | ✅ | BATCH1/BATCH2列表定义清晰 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | 仅print，无logging模块 |
| CSV输出 | N/A | 不生成CSV，写DB |
| 中文文件名 | ✅ | 无 |
| 中断恢复 | ✅ | 返回码判断正确 |

**运行验证：** 批次1: 5/5, 批次2: 1/1 均返回OK。

---

### 2. `I_抓取期货收盘价.py` → `I_FUT_MAIN`

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有因子说明、Header格式 |
| try-except | ✅ | main中有`except Exception` |
| 网络超时 | ⚠️ | akshare底层无显式timeout参数 |
| 魔法数字常量 | ✅ | EXPECTED_MIN=500, EXPECTED_MAX=1200 |
| 类型注解 | ❌ | fetch()/main()均无 |
| 日志记录 | ⚠️ | print，非logging |
| CSV输出 | N/A | 写DB |
| 中文文件名 | ✅ | 无（脚本名除外）|

**运行状态：** 2026-05-02 写入成功，raw_value=796.0, obs_date=2026-04-30 ✅

---

### 3. `I_抓取期货持仓量.py` → `I_FUT_OI`

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有Header格式 |
| try-except | ✅ | main中有`except Exception` |
| 网络超时 | ⚠️ | 同上 |
| 魔法数字常量 | ✅ | EXPECTED_MIN=100000, EXPECTED_MAX=1000000 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | print，非logging |
| CSV输出 | N/A | 写DB |
| 中文文件名 | ✅ | 无 |

**运行状态：** 2026-05-02 写入成功，raw_value=620392.0 ✅

---

### 4. `I_抓取港口库存.py` → `I_STK_PORT`

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有Header格式 |
| try-except | ✅ | main中有`except Exception` |
| 网络超时 | ⚠️ | akshare底层无显式timeout |
| 魔法数字常量 | ✅ | EXPECTED_MIN=0, EXPECTED_MAX=6000 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | printf-style print，非logging |
| CSV输出 | N/A | 写DB |
| 中文文件名 | ✅ | 无 |

**运行状态：** 2026-05-02 写入成功，raw_value=3650.0 ✅

---

### 5. `I_计算基差.py` → `I_SPD_BASIS`

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有Header格式 |
| try-except | ✅ | main中有`except Exception` |
| 网络超时 | ⚠️ | 同上 |
| 魔法数字常量 | ✅ | EXPECTED_MIN=-50, EXPECTED_MAX=50 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | print，非logging |
| CSV输出 | N/A | 写DB |
| 中文文件名 | ✅ | 无 |

**运行状态：** DB中可见`I_SPD_BASIS`因子，今日数据写入待确认

---

### 6. `I_计算近远月价差.py` → `I_SPD_CONTRACT` 🔴严重问题

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有Header格式 |
| try-except | ✅ | main中有`except Exception` |
| 网络超时 | ⚠️ | 同上 |
| 魔法数字常量 | ✅ | EXPECTED_MIN=-50, EXPECTED_MAX=100 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | print，非logging |
| CSV输出 | N/A | 写DB |
| 中文文件名 | ✅ | 无 |

**运行状态：** 🔴 **严重** — DB中最新记录为2026-04-23，今日(2026-05-02)未写入

**根本原因：** L4兜底逻辑只有`print(f"[L4 Fallback]...")`而**没有调用`save_to_db()`**。当`fetch()`失败且`get_latest_value()`返回非None时，脚本只打印不写入，然后正常返回（导致I_run_all.py认为成功）。这是静默数据丢失。

```python
# 问题代码（L4兜底只print，不写DB）
latest = get_latest_value(FACTOR_CODE, SYMBOL)
if latest is not None:
    print(f"[L4 Fallback] {FACTOR_CODE}={latest}")  # ← 只打印，没 save_to_db！
    return
```

---

### 7. `I_批次2_手动输入.py` → BATCH2

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有Header格式 |
| try-except | ✅ | argparse/参数解析有保护 |
| 网络超时 | N/A | 无网络请求 |
| 魔法数字常量 | ✅ | PAID_FACTORS字典定义完整 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | print，非logging |
| CSV输出 | N/A | 无 |
| 中文文件名 | ✅ | 无 |

**运行状态：** ✅ auto模式跳过属预期行为（付费/无免费数据源）

---

## 三、范式共性问题汇总

| 问题 | 影响范围 | 严重程度 |
|------|----------|----------|
| 无函数类型注解 | 全部7个脚本 | ⚠️ 低（Pythonic可选） |
| 使用print而非logging模块 | 全部7个脚本 | ⚠️ 低（日志可grep） |
| akshare调用无显式timeout | 5个采集脚本 | ⚠️ 中（网络抖动可能hang） |
| L4兜底逻辑缺陷 | `I_计算近远月价差.py` | 🔴 高（静默丢数据） |

---

## 四、今日运行结果

```
铁矿石采集结果汇总:
  [OK] I_抓取港口库存.py    → I_STK_PORT = 3650.0
  [OK] I_计算基差.py       → 待确认写入
  [OK] I_抓取期货持仓量.py  → I_FUT_OI = 620392.0
  [OK] I_抓取期货收盘价.py  → I_FUT_MAIN = 796.0
  [OK] I_计算近远月价差.py → 🔴 今日未写入！
  [OK] I_批次2_手动输入.py  → 跳过（预期）
批次1: 5/5
批次2: 1/1
```

DB中`I_SPD_CONTRACT`最新记录仍为2026-04-23 (value=23.5)，今日未更新。

---

## 五、修复建议

### 优先级P0（必须修复）

**`I_计算近远月价差.py` L4兜底逻辑缺陷：**
```python
# 当前（错误）：L4只打印不写DB
latest = get_latest_value(FACTOR_CODE, SYMBOL)
if latest is not None:
    print(f"[L4 Fallback] {FACTOR_CODE}={latest}")
    return  # ← 没有 save_to_db！

# 修复方案：
latest = get_latest_value(FACTOR_CODE, SYMBOL)
if latest is not None:
    print(f"[L4 Fallback] {FACTOR_CODE}={latest} (historical)")
    save_to_db(FACTOR_CODE, SYMBOL, date.today(), date.today(), latest, source_confidence=0.5)
    return
```

### 优先级P1（建议修复）

1. **为5个采集脚本添加类型注解：** `def fetch() -> tuple[float, date]:`
2. **添加显式timeout：** `akshare`内部有requests timeout机制，但建议在`get_latest_value`等工具函数上加装饰器超时
3. **将print替换为logging：** 统一使用`logging.INFO/ERROR`
4. **subprocess.run加timeout：** `I_run_all.py`中建议加30s超时

---

## 六、README.md 更新建议

现有README.md结构良好，建议补充：
1. 新增`I_SPD_CONTRACT`的问题标注（当前只写"✅全部就绪"不准确）
2. 更新"状态摘要"：标注`I_计算近远月价差.py` ⚠️ L4兜底有缺陷
3. 可考虑将"working 6"改为"working 5 / stub 1"（I_批次2_手动输入.py是stub）

---

_复查完成_
