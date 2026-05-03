# Y（豆油）因子采集脚本复查报告

**复查时间**: 2026-05-02 10:17  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\Y\`  
**脚本总数**: 11 个 .py 文件

---

## 一、入口脚本运行结果

```
Y Data Collection @ 2026-05-02 10:17:05
Scripts: 2
>>> Y_棕榈油期货收盘价.py...  [OK] done
>>> Y_棕榈油期货持仓量.py...  [OK] done
Y Done  3.9s  2/2
[OK] All done
```

**注意**: `Y_run_all.py` 仅调度了 2 个脚本（棕榈油系），其余 9 个 stub 脚本未纳入调度。

---

## 二、各脚本范式检查结果

### 2.1 `Y_run_all.py` ✅ 相对最规范

| 检查项 | 状态 | 说明 |
|--------|------|------|
| docstring | ✅ | 有，多行说明 |
| try-except | ✅ | 有（subprocess/timeout） |
| timeout | ✅ | 120s |
| 魔法数字常量 | ⚠️ | 120 硬编码 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | 写日志文件 |
| CSV输出 | ⚠️ | 输出到logs而非output，无CSV |
| 硬编码中文文件名 | ❌ | 无 |
| 中断/恢复逻辑 | ✅ | timeout处理、continue |

### 2.2 `Y_棕榈油期货收盘价.py` ⚠️ 有实际问题采集逻辑，但多项缺失

| 检查项 | 状态 | 说明 |
|--------|------|------|
| docstring | ✅ | 有 |
| try-except | ✅ | 有（L1/L4 fallback） |
| timeout | ❌ | 无，akshare调用无超时 |
| 魔法数字常量 | ❌ | 无，`symbol="Y0"` 硬编码 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | stdout/stderr |
| CSV输出 | N/A | 写DB，无CSV |
| 硬编码中文文件名 | N/A | 无 |
| 中断/恢复逻辑 | ✅ | L4兜底 |

**问题**: AKShare 调用无 timeout；无类型注解；symbol 硬编码；无四层漏斗（仅 L1+L4）。

### 2.3 `Y_棕榈油期货持仓量.py` ⚠️ 同上

| 检查项 | 状态 | 说明 |
|--------|------|------|
| docstring | ✅ | 有 |
| try-except | ✅ | 有（L1/L4 fallback） |
| timeout | ❌ | 无 |
| 魔法数字常量 | ❌ | 无，`symbol="Y0"` 硬编码 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ✅ | stdout/stderr |
| CSV输出 | N/A | 写DB |
| 中断/恢复逻辑 | ✅ | L4兜底 |

### 2.4 `Y_CBOT大豆期货收盘价.py` ⛔ STUB

| 检查项 | 状态 | 说明 |
|--------|------|------|
| docstring | ✅ | 有（Header格式） |
| try-except | ✅ | 有（fallback stub写入） |
| timeout | N/A | 无网络请求 |
| 魔法数字常量 | ✅ | 0.5 硬编码但可接受 |
| 类型注解 | ❌ | 无 |
| 日志记录 | ⚠️ | 仅print，无logger |
| CSV输出 | N/A | stub不输出CSV |
| 实际数据采集 | ❌ | 纯stub，写None，跳过 |

**问题**: 无实际数据采集逻辑（Header标注 ⚠️待修复）；无类型注解；无logger。

### 2.5 `Y_CBOT豆油期货收盘价.py` ⛔ STUB

同上，仅 factor_code 不同。

### 2.6 `Y_豆油与棕榈油价差.py` ⛔ STUB

同上，仅 factor_code 不同。

### 2.7 `Y_豆油商业库存.py` ⛔ STUB

同上，标注付费订阅 Mysteel/隆众。

### 2.8 `Y_豆油期现基差.py` ⛔ STUB

同上。

### 2.9 `Y_豆油期货仓单.py` ⛔ STUB

同上，标注 DCE 接口待验证。

### 2.10 `Y_豆油期货净持仓.py` ⛔ STUB

同上，标注 DCE 接口待验证。

### 2.11 `Y_进口大豆CNF价.py` ⛔ STUB

同上，标注付费订阅。

---

## 三、README.md 现状

**不存在**，需要创建。

---

## 四、汇总问题

| 问题类型 | 数量 | 详情 |
|----------|------|------|
| ⛔ 纯stub（无数据采集） | 9 | 全部CBOT/豆油/价差/库存/基差/仓单/净持仓/CNF |
| ⚠️ 有采集逻辑但缺timeout | 2 | 棕榈油收盘价、棕榈油持仓量 |
| ❌ 无类型注解 | 11 | 全部脚本 |
| ❌ 无logger | 11 | 仅用print/sys.stdout.write |
| ❌ 魔法数字硬编码 | 2 | 棕榈油脚本symbol="Y0" |
| ❌ run_all缺调度 | 9个stub | Y_run_all.py未纳入9个stub脚本 |
| ⚠️ CSV输出路径 | N/A | 规范要求output\，实际写DB |

---

## 五、REVIEW.md 更新内容（供创建 README.md 参考）

```markdown
# Y（豆油）因子采集

品种: Y（豆油）

## 采集因子列表

| 因子代码 | 名称 | 数据源 | 状态 | 备注 |
|----------|------|--------|------|------|
| Y_FUT_CLOSE | 棕榈油期货收盘价 | AKShare L1 | ⚠️运行中/缺timeout | symbol=Y0硬编码 |
| Y_FUT_OI | 棕榈油期货持仓量 | AKShare L1 | ⚠️运行中/缺timeout | symbol=Y0硬编码 |
| Y_FUT_CBOT_SOY | CBOT大豆期货收盘价 | STUB | ⛔待修复 | AKShare接口待验证 |
| Y_FUT_CBOT_OIL | CBOT豆油期货收盘价 | STUB | ⛔待修复 | AKShare接口待验证 |
| Y_SPD_PALM_OIL | 豆油-棕榈油价差 | STUB | ⛔待修复 | AKShare接口待验证 |
| Y_STK_COMMERCIAL | 豆油商业库存 | STUB | ⛔待修复 | 付费订阅Mysteel/隆众 |
| Y_SPD_BASIS | 豆油期现基差 | STUB | ⛔待修复 | 豆油现货待验证 |
| Y_STK_WARRANT | 豆油期货仓单 | STUB | ⛔待修复 | DCE接口待验证 |
| Y_POS_NET | 豆油期货净持仓 | STUB | ⛔待修复 | DCE接口待验证 |
| Y_COST_CNF | 进口大豆CNF价 | STUB | ⛔待修复 | 付费订阅 |

## 脚本说明

| 脚本 | 类型 | 范式合规 | 运行状态 |
|------|------|----------|----------|
| Y_run_all.py | 入口 | ⚠️部分合规 | ✅ 2/2成功 |
| Y_棕榈油期货收盘价.py | 采集 | ⚠️缺timeout/类型注解 | ✅成功 |
| Y_棕榈油期货持仓量.py | 采集 | ⚠️缺timeout/类型注解 | ✅成功 |
| Y_CBOT大豆期货收盘价.py | stub | ❌无采集 | ⛔跳过 |
| Y_CBOT豆油期货收盘价.py | stub | ❌无采集 | ⛔跳过 |
| Y_豆油与棕榈油价差.py | stub | ❌无采集 | ⛔跳过 |
| Y_豆油商业库存.py | stub | ❌无采集 | ⛔跳过 |
| Y_豆油期现基差.py | stub | ❌无采集 | ⛔跳过 |
| Y_豆油期货仓单.py | stub | ❌无采集 | ⛔跳过 |
| Y_豆油期货净持仓.py | stub | ❌无采集 | ⛔跳过 |
| Y_进口大豆CNF价.py | stub | ❌无采集 | ⛔跳过 |

最后更新时间: 2026-05-02
负责人: mimo
```
