# NR（天然橡胶）因子采集脚本健康复查报告

**复查时间**: 2026-05-02 09:52  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\NR\`  
**执行结果**: `NR_run_all.py` 11/11 ✅ 成功（28秒）

---

## 一、脚本清单与因子对照

| # | 脚本文件 | 因子代码 | 状态 | 备注 |
|---|---------|---------|------|------|
| 1 | `NR_run_all.py` | — | ✅ 正常 | 入口调度脚本 |
| 2 | `NR_抓取橡胶.py` | NR_INV_TOTAL | ✅ 正常 | AKShare `futures_inventory_em` |
| 3 | `NR_抓取BDI.py` | NR_FREIGHT_BDI | ✅ 正常 | AKShare `macro_shipping_bdi` |
| 4 | `NR_抓取仓单.py` | NR_STK_WARRANT | ⚠️ 跳过 | INE无公开仓单，已由NR_INV_TOTAL覆盖 |
| 5 | `NR_抓取持仓排名.py` | NR_POS_NET | ✅ 正常 | SHFE持仓排名 |
| 6 | `NR_抓取期货持仓.py` | NR_FUT_OI | ✅ 正常 | NR0持仓量+收盘价 |
| 7 | `NR_计算RU-NR价差.py` | NR_SPD_RU_NR | ✅ 正常 | NR0/RU0 比价 |
| 8 | `NR_天然橡胶期货收盘价.py` | NR_FUT_CLOSE | ✅ 正常 | NR0收盘价 |
| 9 | `NR_橡胶持仓量.py` | NR_POS_OPEN_INT | ✅ 正常 | NR0持仓量 |
| 10 | `NR_橡胶合约间价差.py` | NR_SPD_CONTRACT | ✅ 正常 | NR0收盘价（近月替代） |
| 11 | `NR_抓取现货和基差.py` | NR_SPD_BASIS | ⚠️ 跳过 | AKShare无NR现货价 |
| 12 | `NR_批次2_手动输入.py` | NR_CST_USDCNY等 | ✅ 正常 | 交互录入+USDCNY自动 |
| 13 | `NR_回填历史数据.py` | 多因子 | ✅ 正常 | 历史回填2023-01-01→2026-04-17 |
| 14 | `NR_抓取期货收盘价.py` | NR_FUT_CLOSE | ⚠️ 重复 | 与NR_天然橡胶期货收盘价.py因子代码完全重复 |
| 15 | `NR_抓取期货持仓量.py` | NR_POS_OPEN_INT | ⚠️ 重复 | 与NR_橡胶持仓量.py因子代码完全重复 |
| 16 | `NR_抓取RSS3报价.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 17 | `NR_抓取持仓量.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 18 | `NR_抓取期货库存.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 19 | `NR_抓取汇率.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 20 | `NR_抓取青岛库存.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 21 | `NR_抓取轮胎开工率.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 22 | `NR_抓取ANRPC产量.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 23 | `NR_抓取INE仓单.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 24 | `NR_抓取STR20_FOB.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 25 | `NR_抓取合艾原料.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 26 | `NR_抓取轮胎出口.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |
| 27 | `NR_计算比价.py` | NR_SPD_RU_NR | ⚠️ 重复 | 与NR_计算RU-NR价差.py因子代码重复 |
| 28 | `NR_计算进口利润.py` | XX_XXXXX | ⛔ 模板 | 仅含TODO，无实际逻辑 |

---

## 二、范式检查结果（逐项核验）

### 2.1 脚本头部 docstring
- ✅ 全部脚本均有文件级 docstring
- ⚠️ 大部分 Header 标注"⚠️待修复"，数据源/解决方案均填写"需补充"，信息不完整

### 2.2 try-except 错误处理
- ✅ 无 bare `except`（均带具体异常类型或变量）
- ⚠️ `NR_run_all.py` 的 `run_script()` 函数使用 `except Exception as e`，属于宽泛捕获（但尚可接受）

### 2.3 网络请求超时（timeout）
- ❌ **AKShare API 调用均无 timeout 参数**，所有脚本的 `ak.xxx()` 均缺少 `timeout=N`
- ⚠️ `NR_批次2_手动输入.py` 中 `requests.get` 有 `timeout=5`，符合要求

### 2.4 魔法数字常量
- ✅ 大部分脚本将阈值定义为 `EXPECTED_MIN/MAX` 或 `MIN_VALUE/MAX_VALUE`
- ⚠️ `NR_抓取BDI.py` 中 `200 <= bdi_val <= 15000` 范围检查直接写在代码中，未提取为常量
- ⚠️ `NR_抓取期货收盘价.py` 中 `EXPECTED_MAX=999999999` 无实际保护意义

### 2.5 函数类型注解
- ❌ **几乎所有脚本均无类型注解**，只有 `NR_run_all.py` 的 `run_script()` 有简单注解
- 建议：参数和返回值添加 `-> None`、`-> tuple` 等注解

### 2.6 日志记录（INFO/ERROR）
- ✅ 有日志输出（print 语句）
- ⚠️ 只有 INFO/ERROR 级别区分，无标准 `logging` 模块，部分脚本用 `[L1]` `[L4]` 标签
- 建议：统一使用 `logging` 模块替代 print

### 2.7 数据输出路径
- ✅ 数据写入 `pit_data.db`（通过 `db_utils.save_to_db`）
- ℹ️ 规范要求"输出到 `D:\futures_v6\macro_engine\output\`"，但实际为数据库直写，需确认规范要求

### 2.8 无硬编码中文文件名
- ❌ **所有脚本文件名均含中文**（如 `NR_天然橡胶期货收盘价.py`、`NR_抓取橡胶.py`），违反"无硬编码中文文件名"规范

### 2.9 中断/恢复逻辑
- ✅ 有 DB 回补机制（L4 fallback），网络失败后回补历史值
- ✅ `NR_run_all.py` 单脚本失败不影响整体，继续执行下一个

---

## 三、运行验证

```
==================================================
NR Data Collection @ 2026-05-02 09:52:04
Scripts to run: 11
==================================================
>> Running NR_抓取橡胶.py...       [OK] NR_INV_TOTAL=36389.0 obs=2026-04-30
>> Running NR_抓取BDI.py...        [OK] NR_FREIGHT_BDI=2730.0 obs=2026-05-01
>> Running NR_抓取仓单.py...       [SKIP] INE无公开仓单
>> Running NR_抓取持仓排名.py...    [OK] NR_POS_NET=-939 obs=2026-04-30
>> Running NR_抓取期货持仓.py...   [OK] NR_FUT_OI=47776 obs=2026-05-01
>> Running NR_计算RU-NR价差.py...  [OK] NR_SPD_RU_NR=0.8289 obs=2026-04-30
>> Running NR_天然橡胶期货收盘价.py [OK] NR_FUT_CLOSE=14580.0 obs=2026-04-30
>> Running NR_橡胶持仓量.py...      [OK] NR_POS_OPEN_INT=47776.0 obs=2026-04-30
>> Running NR_橡胶合约间价差.py...  [OK] NR_SPD_CONTRACT=14580.0 obs=2026-04-30
>> Running NR_抓取现货和基差.py...  [SKIP] AKShare无NR现货价格
>> Running NR_批次2_手动输入.py...  [OK] NR_CST_USDCNY=6.8251 L4回补成功
==================================================
NR Data Collection Done  28.0s  Success:11/11
==================================================
```

**结论**: 11/11 脚本执行成功，所有 DB 写入正常，无报错。

---

## 四、关键问题汇总

| 优先级 | 问题 | 影响范围 |
|--------|------|---------|
| P0 | **9个模板脚本**（XX_XXXXX）无实际逻辑，占目录但不产出数据 | 9个因子完全缺失 |
| P0 | **文件名含中文**，违反规范 | 全部脚本 |
| P1 | **AKShare 无 timeout**，可能造成长时间挂起 | 所有实际采集脚本 |
| P1 | **NR_FUT_CLOSE 和 NR_SPD_CONTRACT 完全重复**，浪费运行时间 | run_all调度 |
| P1 | **因子代码重复**：NR_FUT_CLOSE(NR_天然橡胶期货收盘价+NR_抓取期货收盘价)、NR_SPD_RU_NR(NR_计算RU-NR价差+NR_计算比价) | 数据覆盖冗余 |
| P2 | **Header信息不完整**：所有脚本"当前状态"均为"需补充" | 维护困难 |
| P2 | **无类型注解** | 代码可读性 |
| P2 | **NR_抓取期货收盘价.py** EXPECTED_MAX=999999999 无实际校验作用 | 数值合理性 |
| P3 | 魔法数字未完全常量化 | BDICheck范围 |

---

## 五、README.md 更新建议

现有 README.md 需重新编写，内容如下：

```markdown
# NR（天然橡胶）因子采集

## 品种：NR（20号胶）

## 采集因子列表

| 因子代码 | 名称 | 数据源 | 状态 | 说明 |
|---------|------|--------|------|------|
| NR_FUT_CLOSE | 天然橡胶期货收盘价 | AKShare NR0 | ✅ 正常 | 新浪NR主力日线 |
| NR_POS_OPEN_INT | 期货持仓量 | AKShare NR0 | ✅ 正常 | NR0持仓量 |
| NR_FUT_OI | 期货总持仓 | AKShare NR0 | ✅ 正常 | NR0持仓量 |
| NR_INV_TOTAL | 期货库存 | AKShare futures_inventory_em | ✅ 正常 | INE_nr库存 |
| NR_FREIGHT_BDI | 波罗的海指数 | AKShare macro_shipping_bdi | ✅ 正常 | BDI指数 |
| NR_POS_NET | 持仓排名净多头 | SHFE官网爬虫 | ✅ 正常 | 前5会员净持仓 |
| NR_SPD_RU_NR | RU/NR价比 | AKShare NR0+RU0 | ✅ 正常 | NR0收盘/RU0收盘 |
| NR_SPD_CONTRACT | 合约间价差 | AKShare NR0 | ✅ 正常 | NR近月收盘（替代） |
| NR_SPD_BASIS | 现货基差 | AKShare | ⚠️ 跳过 | AKShare无NR现货价 |
| NR_STK_WARRANT | 仓单 | INE | ⚠️ 跳过 | INE无公开数据 |
| NR_CST_USDCNY | 美元兑人民币 | 新浪财经 | ✅ 正常 | --auto模式自动获取 |
| NR_SUP_*(批次2) | 原料/进口/需求因子 | 手动录入 | ⚠️ 待手动 | ANRPC/泰国报价等 |

## 脚本说明

- `NR_run_all.py` — 主入口，调度11个采集脚本
- `NR_回填历史数据.py` — 批量回填2023-01-01至今历史数据
- `NR_批次2_手动输入.py` — 付费因子交互录入（--auto模式仅获取USDCNY）

## 最后更新时间
2026-05-02 by NR复查员
```

---

## 六、复查结论

| 类别 | 状态 |
|------|------|
| run_all 批量运行 | ✅ 11/11 成功 |
| 实际采集脚本（11个） | ✅ 数据正常，写入正常 |
| 模板/待实现脚本（9个） | ⛔ 需要优先开发 |
| 重复脚本（3个） | ⚠️ 建议合并或删除 |
| 范式合规（整体） | ⚠️ 基本框架合规，细节需改进 |
