# EG 因子采集脚本复查报告

**复查时间**: 2026-05-02 09:29
**工作目录**: `D:\futures_v6\macro_engine\crawlers\EG\`
**运行验证**: `EG_run_all.py` → 3/3 成功，耗时 5.8s

---

## 一、脚本清单与检查结果

| # | 脚本名 | 实际功能 | 范式合规 | 备注 |
|---|--------|---------|---------|------|
| 1 | `EG_run_all.py` | 入口脚本（subprocess调度） | ⚠️ 部分合规 | 使用print+文件日志，非标准logging |
| 2 | `EG_乙二醇期货收盘价.py` | AKShare L1采集 | ⚠️ 待修复 | 缺类型注解，无网络超时 |
| 3 | `EG_乙二醇期货持仓量.py` | AKShare L1采集 | ⚠️ 待修复 | 同上 |
| 4 | `EG_乙二醇工厂库存.py` | AKShare L1采集 | ⚠️ 待修复 | 同上 |
| 5 | `EG_乙二醇期现基差.py` | 付费stub（写None） | ⛔ 不合规 | 违反raw_value数值型禁止规定 |
| 6 | `EG_乙二醇期货净持仓.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |
| 7 | `EG_乙二醇装置开工率.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |
| 8 | `EG_华东乙二醇港口库存.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |
| 9 | `EG_煤制乙二醇开工率.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |
| 10 | `EG_石脑油裂解价差.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |
| 11 | `EG_聚酯企业乙二醇库存.py` | 付费stub（写None） | ⛔ 不合规 | 同上 |

---

## 二、逐项范式检查

### 2.1 `EG_run_all.py`（入口脚本）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 头部docstring | ✅ | `EG_run_all.py - 乙二醇数据采集（subprocess模式）` |
| try-except（禁止bare except） | ✅ | 有`except Exception` |
| 网络超时设置 | ✅ | `subprocess.run(timeout=120)` |
| 魔法数字常量 | ✅ | `timeout=120` |
| 类型注解 | N/A | 无函数签名类型注解 |
| 日志记录（INFO/ERROR） | ⚠️ | 使用`print()`写入文件日志，非标准logging |
| CSV输出路径 | N/A | 日志输出，非CSV |
| 无硬编码中文文件名 | ✅ | `f"{now.strftime('%Y-%m-%d')}_EG.log"` |
| 中断/恢复逻辑 | ✅ | 跳过不存在的脚本，记录失败列表 |

**运行日志**:
```
EG Data Collection @ 2026-05-02 09:29:30
Scripts: 3
>>> EG_乙二醇期货收盘价.py...
[OK] EG_乙二醇期货收盘价.py done
>>> EG_乙二醇期货持仓量.py...
[OK] EG_乙二醇期货持仓量.py done
>>> EG_乙二醇工厂库存.py...
[OK] EG_乙二醇工厂库存.py done
EG Done  5.8s  3/3
[OK] All done
```

---

### 2.2 数据采集脚本（2/3/4号）

以`EG_乙二醇期货收盘价.py`为代表：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 头部docstring | ✅ | 结构完整，有Header模板 |
| try-except（禁止bare except） | ✅ | `except Exception as e` |
| 网络超时设置 | ❌ | AKShare内部有超时，但代码层未显式设置 |
| 魔法数字常量 | ✅ | `FACTOR_CODE`, `SYMBOL`已定义 |
| 类型注解 | ❌ | `run(auto=False)` 无类型注解 |
| 日志记录（INFO/ERROR） | ⚠️ | 使用`sys.stdout.write`，非标准logging |
| CSV输出路径 | N/A | 数据直接写入`pit_data.db` |
| 无硬编码中文文件名 | ✅ | 数据写入数据库 |
| 中断/恢复逻辑 | ✅ | L4回补逻辑完整 |

**已知问题**:
- 缺`requests`层超时（AKShare内部实现，不透明）
- 函数缺类型注解

---

### 2.3 付费stub脚本（5~11号）

8个stub脚本结构完全一致，以`EG_乙二醇期现基差.py`为代表：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 头部docstring | ✅ | 有Header |
| try-except | ✅ | `except Exception as e` |
| 网络超时设置 | N/A | 无网络请求 |
| 魔法数字常量 | ✅ | `_FACTOR_CODE`等常量定义 |
| 类型注解 | ❌ | `run(auto=False)` 无类型注解 |
| 日志记录 | ⚠️ | 使用`print`，非标准logging |
| CSV输出路径 | N/A | DB |
| 无硬编码中文文件名 | ✅ | N/A |
| 中断/恢复逻辑 | ⚠️ | 跳过所有层直接写stub |

**严重违规**:
1. **写入`raw_value=None`** — 违反"禁止写入非数值型raw_value"红线
2. **直接写L4 stub，未尝试L1免费源** — 违反"禁止跳过四层漏斗"红线
3. **get_pit_dates() fallback返回值顺序为`(obs_date, pub_date)`**，与common.db_utils的`(pub_date, obs_date)`顺序不一致，导致参数顺序歧义

---

## 三、run_all.py覆盖度问题

`EG_run_all.py`只调度了3个脚本：
```python
scripts = [
    "EG_乙二醇期货收盘价.py",
    "EG_乙二醇期货持仓量.py",
    "EG_乙二醇工厂库存.py",
]
```

剩余8个stub脚本**完全未被调度**，等同于永久跳过。

---

## 四、核心问题汇总

### P0（必须修复）

| # | 问题 | 影响脚本 | 修复方案 |
|---|------|---------|---------|
| 1 | 写入`raw_value=None` | 5~11号 | 删除stub脚本，不写占位符；或补充L1~L3免费数据源尝试 |
| 2 | stub直接跳过L1~L3 | 5~11号 | 按四层漏斗逐层实现（如EG_期现基差应尝试AKShare/交易所API） |
| 3 | run_all.py未包含所有脚本 | run_all.py | 将8个stub脚本加入调度列表，或明确标记为"手动模式" |

### P1（建议修复）

| # | 问题 | 影响脚本 | 修复方案 |
|---|------|---------|---------|
| 4 | AKShare调用无显式timeout | 2/3/4号 | 封装requests层并设置`timeout=30` |
| 5 | 函数缺类型注解 | 全部 | 添加`def run(auto: bool = False) -> int:` |
| 6 | print()非标准logging | 全部 | 替换为`logging.getLogger(__name__)` |
| 7 | `get_pit_dates()` fallback顺序与common不一致 | 5~11号 | 统一为`return (pub_date, obs_date)` |

---

## 五、README.md 更新内容

```markdown
# EG 乙二醇 - 采集因子一览

| 因子代码 | 中文名 | 数据源 | 状态 | 备注 |
|----------|--------|--------|------|------|
| EG_FUT_CLOSE | 乙二醇期货收盘价 | AKShare L1 | ✅ 正常 | EG0主力合约 |
| EG_FUT_OI | 乙二醇期货持仓量 | AKShare L1 | ✅ 正常 | EG0主力合约 |
| EG_STK_WARRANT | 乙二醇工厂库存 | AKShare L1 | ✅ 正常 | 隆众资讯(免费聚合) |
| EG_SPD_BASIS | 乙二醇期现基差 | 待开发 | ⛔ 待配 | 需付费订阅CCF |
| EG_POS_NET | 大商所前20净持仓 | 待开发 | ⛔ 待配 | DCE接口待验证 |
| EG_STK_PLANT_RATE | 乙二醇装置开工率 | 待开发 | ⛔ 待配 | 需付费订阅CCF |
| EG_STK_PORT | 华东乙二醇港口库存 | 待开发 | ⛔ 待配 | 需付费订阅CCF/隆众 |
| EG_STK_COAL_RATE | 煤制乙二醇开工率 | 待开发 | ⛔ 待配 | 需付费订阅隆众资讯 |
| EG_SPT_NAPTHA | 石脑油裂解价差 | 待开发 | ⛔ 待配 | AKShare接口待验证 |
| EG_STK_POLYESTER | 聚酯企业乙二醇库存 | 待开发 | ⛔ 待配 | 需付费订阅CCF |

## 脚本说明

| 脚本 | 范式合规 | 运行状态 |
|------|---------|---------|
| EG_run_all.py | ⚠️ | ✅ 3/3成功 |
| EG_乙二醇期货收盘价.py | ⚠️ 缺类型注解/超时 | ✅ |
| EG_乙二醇期货持仓量.py | ⚠️ 缺类型注解/超时 | ✅ |
| EG_乙二醇工厂库存.py | ⚠️ 缺类型注解/超时 | ✅ |
| EG_乙二醇期现基差.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_乙二醇期货净持仓.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_乙二醇装置开工率.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_华东乙二醇港口库存.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_煤制乙二醇开工率.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_石脑油裂解价差.py | ⛔ 写None违反规范 | ❌ 未调度 |
| EG_聚酯企业乙二醇库存.py | ⛔ 写None违反规范 | ❌ 未调度 |

## 最后更新
- 时间: 2026-05-02
- 负责人: 程序员mimo
- 复查结果: 3个采集脚本正常，8个stub脚本存在P0违规需修复
```

---

## 六、复查结论

**采集脚本（3个）**: 运行正常，但存在P1级问题（类型注解、显式超时、logging规范化）
**Stub脚本（8个）**: 全部P0违规，违反"禁止写入None"和"禁止跳过四层漏斗"两条红线，建议优先按L1~L3顺序补充免费数据源后删除stub状态
