# PB（铅）因子采集脚本复查报告

**复查日期：** 2026-05-02  
**复查人：** 程序员mimo（subagent）  
**工作目录：** `D:\futures_v6\macro_engine\crawlers\PB\`

---

## 一、脚本清单与检查结果

| # | 脚本名 | 因子代码 | 实际功能 | 采集层 | 运行状态 |
|---|--------|---------|---------|--------|---------|
| 1 | `PB_run_all.py` | — | 入口调度器 | — | ✅ 正常 |
| 2 | `PB_沪铅期货收盘价.py` | `PB_FUT_CLOSE` | 沪铅期货收盘价 | L1（AKShare） | ✅ 正常 |
| 3 | `PB_沪铅期货持仓量.py` | `PB_FUT_OI` | 沪铅期货持仓量 | L1（AKShare） | ✅ 正常 |
| 4 | `PB_SMM沪铅现货价格.py` | `PB_PB_SPT_SMM` | SMM沪铅现货价格 | L4 stub | ⚠️ 待修复 |
| 5 | `PB_原生铅与再生铅价差.py` | `PB_PB_SPD_PRI_VIRGIN` | 原生/再生铅价差 | L4 stub | ⚠️ 待修复 |
| 6 | `PB_沪铅期现基差.py` | `PB_PB_SPD_BASIS` | 沪铅期现基差 | L4 stub | ⚠️ 待修复 |
| 7 | `PB_沪铅期货净持仓.py` | `PB_PB_POS_NET` | 上期所前20净持仓 | L4 stub | ⚠️ 待修复 |
| 8 | `PB_沪铅期货近远月价差.py` | `PB_PB_SPD_NEAR_FAR` | 沪铅近远月价差 | L4 stub | ⚠️ 待修复 |
| 9 | `PB_美元兑人民币汇率.py` | `PB_PB_FX_USDCNY` | 美元兑人民币汇率 | L4 stub | ⚠️ 待修复 |
| 10 | `PB_铅TC加工费.py` | `PB_PB_MACRO_TC` | 铅矿加工费 | L4 stub | ⚠️ 待修复 |
| 11 | `PB_铅酸电池用铅占比.py` | `PB_PB_STK_BATTERY_RATE` | 铅酸蓄电池开工率 | L4 stub | ⚠️ 待修复 |
| 12 | `PB_铅锭仓单库存.py` | `PB_PB_STK_WARRANT` | 上期所沪铅仓单 | L4 stub | ⚠️ 待修复 |
| 13 | `PB_铅锭社会库存.py` | `PB_PB_STK_SOCIAL` | 铅锭社会库存 | L4 stub | ⚠️ 待修复 |

---

## 二、逐项范式核验

### 2.1 PB_run_all.py（入口调度器）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | 有文件级docstring |
| try-except | ✅ | `except Exception as e` + `subprocess.TimeoutExpired` |
| timeout | ✅ | `subprocess.run(timeout=120)` |
| 魔法数字常量 | ⚠️ | `scripts = ["PB_沪铅期货收盘价.py", ...]` 硬编码列表，但可接受 |
| 类型注解 | ❌ | `run_all()` 无返回类型注解 |
| 日志 | ✅ | 写日志文件 + 打印输出 |
| CSV输出 | N/A | 不产生CSV，调度子进程 |
| 硬编码中文文件名 | ✅ | 调用子脚本文件名，无中文 |
| 中断/恢复 | ❌ | 无checkpoint逻辑 |

**问题：** 仅调度 2 个脚本（`PB_沪铅期货收盘价.py`、`PB_沪铅期货持仓量.py`），其余 11 个因子脚本未被纳入。

---

### 2.2 PB_沪铅期货收盘价.py（因子脚本 L1 范本）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | 有完整Header（因子名、公式、状态） |
| try-except | ✅ | `except Exception as e` + L4兜底 |
| timeout | ⚠️ | AKShare内部timeout，未显式传参 |
| 魔法数字常量 | ✅ | `FACTOR_CODE`, `SYMBOL` 常量 |
| 类型注解 | ❌ | `main()` 无类型注解 |
| 日志 | ✅ | `sys.stdout.write` / `sys.stderr.write` |
| CSV输出 | N/A | 直接写DB，无CSV |
| 硬编码中文文件名 | N/A | 文件名即因子名，合理 |
| 中断/恢复 | ✅ | L4 fallback逻辑 |

**实际运行：**
```
(auto) === PB_FUT_CLOSE === obs=2026-05-01
[DB] 写入成功: PB_FUT_CLOSE = 16630.0
[L1] PB_FUT_CLOSE=16630.0 (2026-04-30) done
```
✅ 成功获取 2026-04-30 沪铅期货收盘价 16630.0，写入DB。

---

### 2.3 PB_沪铅期货持仓量.py（L1）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | 有完整Header |
| try-except | ✅ | `except Exception as e` + L4兜底 |
| timeout | ⚠️ | AKShare内部timeout，未显式传参 |
| 魔法数字常量 | ✅ | `FACTOR_CODE`, `SYMBOL` 常量 |
| 类型注解 | ❌ | `main()` 无类型注解 |
| 日志 | ✅ | `sys.stdout.write` / `sys.stderr.write` |
| CSV输出 | N/A | 直接写DB，无CSV |
| 硬编码中文文件名 | N/A | 合理 |
| 中断/恢复 | ✅ | L4 fallback逻辑 |

**实际运行：**
```
(auto) === PB_FUT_OI === obs=2026-05-01
[DB] 写入成功: PB_FUT_OI = 63295.0
[L1] PB_FUT_OI=63295.0 (2026-04-30) done
```
✅ 成功获取 2026-04-30 沪铅期货持仓量 63295.0，写入DB。

---

### 2.4 L4 Stub 脚本（11个：SMM沪铅/原生铅价差/期现基差/净持仓/近远月价差/美元汇率/TC加工费/电池占比/仓单库存/社会库存）

**共性问题：**

| 检查项 | 结果 | 说明 |
|--------|------|------|
| docstring | ✅ | 有Header，标注"当前状态: ⚠️待修复" |
| try-except | ✅ | `except Exception as e` |
| timeout | N/A | 无网络请求 |
| 魔法数字常量 | ✅ | `_FACTOR_SYMBOL`, `_FACTOR_CODE`, `_FACTOR_FC`, `_FACTOR_REASON` |
| 类型注解 | ❌ | `run(auto=False)` 无类型注解 |
| 日志 | ⚠️ | 用 `print()` 输出，无分级（INFO/ERROR） |
| CSV输出 | N/A | 直接写DB |
| 硬编码中文文件名 | ✅ | 文件名即因子名 |
| 中断/恢复 | N/A | stub，无实际采集 |

**共性结论：** 11个Stub脚本均只写L4占位符（`raw_value=None`, `source_confidence=0.5`），等待付费订阅接入。

---

## 三、关键发现

### 3.1 采集覆盖率：2/13（仅 15%）

| 类别 | 数量 | 因子 |
|------|------|------|
| L1（免费源） | 2 | PB_FUT_CLOSE, PB_FUT_OI |
| L4 Stub（付费待配） | 11 | SMM现货/原生铅价差/期现基差/净持仓/近远月价差/汇率/TC/电池占比/仓单/社会库存 |

**问题：** 四层漏斗只实现了第一层（L1），其余11个因子全部停在L4 Stub，无L2/L3免费数据源验证。

### 3.2 脚本分类错误

`PB_run_all.py` 的 `scripts` 列表只有 2 个脚本，其余 11 个因子脚本完全未被 run_all 调度。需要将所有因子脚本统一纳入调度（按优先级：L1 → L4 Stub）。

### 3.3 CSV输出规范问题

- 范式要求："数据输出路径与 CSV 规范一致（输出到 `D:\futures_v6\macro_engine\output\`）"
- 实际情况：所有脚本均无CSV输出，直接写DB（`pit_data.db`）
- **判断：** 实际系统设计为DB直写，CSV输出是旧规范遗留要求。建议统一说明：PB因子输出至 `pit_data.db`，CSV为其他品种输出格式。

### 3.4 类型注解缺失

所有脚本的 `main()` / `run()` 函数均无返回类型注解（`-> int`）。这是范式要求的缺陷。

### 3.5 日志输出含乱码

`2026-05-02_PB.log` 中含有大量乱码字符（如 `娌熵タ鏈熻揣鏀剁洏浠敤.py`），说明 `subprocess` 捕获子进程stdout时编码处理有问题。虽然脚本内已 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`，但子进程传递的 `-X utf8=1` 参数在Windows GBK环境下仍会导致中文参数名乱码。

---

## 四、运行验证日志

```
PB Start @ 2026-05-02 01:04:37.165056
--- PB_沪铅期货收盘价.py @ 2026-05-02 01:04:37.165056 ---
(auto) === PB_FUT_CLOSE === obs=2026-04-30
[DB] 写入成功: PB_FUT_CLOSE = 16630.0
[L1] PB_FUT_CLOSE=16630.0 (2026-04-30) done

--- PB_沪铅期货持仓量.py @ 2026-05-02 01:04:38.960133 ---
(auto) === PB_FUT_OI === obs=2026-05-01
[DB] 写入成功: PB_FUT_OI = 63295.0
[L1] PB_FUT_OI=63295.0 (2026-04-30) done

[Done] 2/2
```

结论：2个L1脚本均可正常采集数据并写入DB，无报错。

---

## 五、待办事项

| 优先级 | 事项 | 负责人 |
|--------|------|--------|
| P0 | `PB_run_all.py` scripts列表补全11个Stub脚本 | mimo |
| P1 | 为11个Stub脚本补充L2/L3数据源验证（四层漏斗逐层尝试） | mimo |
| P1 | 给所有 `main()` / `run()` 函数补类型注解 `-> int` | mimo |
| P2 | 修复子进程中文参数名乱码问题（log文件） | mimo |
| P2 | 统一CSV输出规范说明（DB直写 vs CSV文件） | mimo |
| P3 | 补充 `PB_沪铅期现基差.py` 的SHFE现货价格数据源（免费） | mimo |

---

*报告生成时间：2026-05-02 09:56 GMT+8*
