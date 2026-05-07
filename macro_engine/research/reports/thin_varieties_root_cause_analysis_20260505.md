# 薄弱品种数据缺失：根因分析与修复方案
**日期：2026-05-05 | 更新：2026-05-06 | 分析：因子分析师YIYI**
**涉及品种：EC / LC / LH / PB / PP / SC / SN / Y / J / I / P / HC（12个）**

---

## 一、核心结论

**这不是 bug，是架构设计决策的必然结果。**

系统为每个计划的因子都写了脚本（即使数据源不可用），脚本在检测到付费/不可用源时优雅退出，不写数据。结果是：系统知道自己缺什么，但无法在无订阅的情况下修复。

---

## 二、数据缺失的四种根因

通过对比 PIT 数据库实际数据 + 采集日志 + 各品种交付文档，12个品种的数据缺口可精确归因如下：

### 根因分布（按因子计）

| 根因 | 占比 | 说明 |
|------|------|------|
| **付费源 · 脚本存在但不写数据** | ~50% | SMM/隆众/卓创/汾渭/Mysteel深度等付费源，脚本检测后主动跳过 |
| **免费API异常 · 脚本存在但调用失败** | ~25% | SHFE/DCE官网接口返回格式变化，脚本未适配 |
| **从未实现 · 免费源但没人写脚本** | ~15% | AKShare有数据（EIA/SCFI/OPEC等），但品种只有3-4个最基础脚本 |
| **正常工作** | ~10% | FUT_CLOSE + FUT_OI 来自 AKShare，稳定产出 |

---

## 三、逐品种根因拆解（含执行级API细节）

### 3.1 PB（沪铅）— 14个脚本 → PIT仅2因子

| 状态 | 因子数 | 举例 |
|------|--------|------|
| 付费跳过 | 5 | SMM现货价、原生/再生铅价差、TC加工费、蓄电池开工率、社会库存 |
| SHFE API 异常 | 4 | 仓单、净持仓、期现基差、近远月价差 |
| 委托其他品种 | 1 | USDCNY（已由 shared 爬虫统一采集） |
| ✅ 正常采集 | 2 | FUT_CLOSE、FUT_OI |

**修复路线**：仓单用 `futures_shfe_warehouse_receipt`，持仓用 `get_shfe_rank_table(date="YYYYMMDD")`，基差用 `futures_to_spot_shfe`。

> **进展 2026-05-06**：PB_POS_NET 已修复并验证入库（net=-462, obs=2026-04-30）。剩余 3 个待 mimo 逐项修复。

### 3.2 PP（聚丙烯）— 13个脚本 → PIT仅2因子

| 状态 | 因子数 | 举例 |
|------|--------|------|
| 付费跳过 | 7 | CFR中国报价、拉丝料/共聚价差、LLDPE-PP价差、港口库存、编织袋开工率、装置开工率 |
| DCE API 异常 | 3 | 仓单、净持仓、期现基差 |
| ✅ 正常采集 | 2 | FUT_CLOSE、FUT_OI |

**修复路线**：DCE仓单用 `futures_dce_warehouse_receipt`，持仓排名可能需用 `get_dce_rank_table`，基差用 `futures_spot_price`。

### 3.3 Y（豆油）— 12个脚本 → PIT仅3因子

| 状态 | 因子数 | 举例 |
|------|--------|------|
| 付费跳过 | 4 | 进口大豆CNF价、豆粕/豆油价差、行业库存、现货价 |
| API 异常 | 3 | 仓单、基差、月差 |
| ✅ 正常采集 | 3 | FUT_CLOSE、FUT_OI、CBOT大豆（仅1次成功） |

**修复路线**：同 DCE 接口体系，CBOT大豆因子需检查跨源稳定性（CBOT→AKShare）。

### 3.4 HC（热轧卷板）— 15个脚本 → PIT仅3因子

| 状态 | 因子数 | 举例 |
|------|--------|------|
| 付费跳过 | 6 | Mysteel现货、热卷库存、HC-RB价差、钢厂日产量、周产量、制造业PMI详情 |
| API 异常 | 5 | 仓单、净持仓、基差、月差、钢厂开工率 |
| ✅ 正常采集 | 3 | FUT_CLOSE、FUT_OI、PMI_MFG（1行） |

**修复路线**：对照 RB（螺纹钢）的 SHFE API 调用方式修正——RB 正常采集说明数据源没问题，是 HC 脚本实现有差异。

### 3.5 J（焦炭）— 13个脚本 → PIT 5个因子，全部只有1行

| 状态 | 因子数 | 举例 |
|------|--------|------|
| 付费跳过 | 3 | 焦炭出口FOB（隆众/卓创）、钢厂焦炭可用天数（Mysteel）、焦化企业开工率（汾渭/Mysteel）|
| AKShare 部分失败 | 1 | J1（焦炭次月合约）futures_main_sina 返回空，近远月价差不可用 |
| ✅ 正常采集（已修复） | 5 | FUT_CLOSE/SPD_BASIS/SPD_J_JM/SPT_CCI/SPT_MYSTEL |

**J 的独特问题**：5个因子各只有1行，根因在 `db_utils.py` 的 `_save_with_retry()`——置信度检查只匹配 `(factor_code, symbol, obs_date)`，不匹配 `pub_date`。同 obs_date 不同 pub_date 的记录被拦截。

> **进展 2026-05-06**：R1（db_utils.py 修复）已部署，J 的 5 个因子已开始积累多日记录（pub=2026-05-06 的新记录写入成功）。

### 3.6 EC/LC/LH/SC（仅有3-4个脚本，严重脚本不足）

| 品种 | PIT因子 | 免费可采但未实现 | 数据源 | 付费源 |
|------|---------|-----------------|--------|--------|
| EC | 2个 | SCFIS欧线现货指数 | `akshare.scfi_index()` | — |
| EC | | SCFI综合运价指数 | `akshare.scfi_index()` | — |
| EC | | EC期现基差 | SCFIS - EC主力 | — |
| EC | | EC近远月价差 | AKShare futures_spread | — |
| EC | | INE前20净持仓 | `ine_position_rank` | — |
| EC | | USD/CNY汇率 | shared 已有 | — |
| LC | 2个 | 碳酸锂现货（电池级） | `akshare.energy_index()` / 生意社 | 2个 |
| LC | | LC期现基差 | 现货 - LC主力 | |
| LC | | LC近远月价差 | AKShare futures_spread | |
| LC | | 新能源车产量同比 | `akshare.macro_china()` | |
| LH | 2个 | 全国外三元生猪均价 | `akshare.hog_price()` / 猪e网 | 1个 |
| LH | | LH期现基差 | 现货 - 主力 | |
| LH | | 能繁母猪存栏量 | 农业农村部月度报告 | |
| LH | | 仔猪价格 | 博亚和讯 / 涌益 | |
| LH | | 猪粮比价 | 发改委 / 博亚和讯 | |
| SC | 2个 | EIA美国原油库存 | `akshare.eia_crude_stock()` | — |
| SC | | 布伦特-WTI价差 | AKShare | |
| SC | | SC期现基差 | SC主力 - 国际原油 | |
| SC | | SC近远月价差 | AKShare futures_spread | |
| SC | | OPEC月度产量 | OPEC官网 scraping | |
| SC | | 美国原油产量 | EIA.gov | |
| SC | | 裂解价差 | AKShare | |
| SC | | 美元指数DXY | `akshare.fx_spot_quote` | |

**SC 是最冤的品种——全部8个核心因子都是免费公开数据，只是脚本没写。**

### 3.7 SN/I/P（部分因子有历史，部分极薄）

| 品种 | 工作正常 | 极薄但可回填 | 完全缺失 |
|------|---------|------------|---------|
| SN | CLOSE/OI/DCE_INV（71-800行）| — | SMM现货/基差/月差/LME3M/库存（5个）|
| I | CLOSE/OI（800行）| MAIN/STK_PORT/SPD_BASIS/SPD_CONTRACT（各2-3行）| — |
| P | CLOSE/OI（800行）| OIL_REF/SPD_BASIS/SPD_CONTRACT（各1-3行）| 马盘FOB价（1个）|

---

## 四、总缺口量化

| 问题类别 | 涉及品种数 | 可修复因子数 | 所需条件 |
|----------|-----------|-------------|----------|
| **付费源 · 无解** | 全部12个 | ~45个因子 | 需 SMM/隆众/卓创/汾渭/Mysteel 订阅 |
| **免费API异常 · 可修** | PB/PP/Y/HC/J（5个）| ~18个因子 | 修正 SHFE/DCE API 调用 |
| **从未实现 · 可写** | EC/LC/LH/SC/SN（5个）| ~30个因子 | 开发新爬虫脚本 |
| **置信度阻断 · 可修** | 全部（J最严重）| ✔ 已修复 | db_utils.py 已改 |
| **极薄需回填 · 可补** | I/P（2个）| ~7个因子 | 历史数据回填 |

---

## 五、修复方案（按投入产出比排序）

### R1 ✅ 已完成 — 修正 db_utils.py 置信度匹配逻辑（2026-05-06）

```
原: WHERE factor_code=? AND symbol=? AND obs_date=?
改: WHERE factor_code=? AND symbol=? AND pub_date=? AND obs_date=?
```
- 影响：J 的 5 个因子从"各 1 行"变"每个市场日 1 行"
- 验证通过：2026-05-06 新 pub_date 记录写入成功

### R2 🔄 进行中 — 修复 SHFE/DCE 免费 API 脚本（PB/PP/Y/HC/J）

| 品种 | 可修复因子 | API 接口 |
|------|-----------|---------|
| PB | 仓单、净持仓、基差、月差（4个）| `futures_shfe_warehouse_receipt` / `get_shfe_rank_table` / `futures_to_spot_shfe` |
| PP | 仓单、净持仓、基差（3个）| `futures_dce_warehouse_receipt` / `get_dce_rank_table` / `futures_spot_price` |
| Y | 仓单、基差、月差（3个）| 同上 DCE 体系 |
| HC | 仓单、净持仓、基差、月差（4个）| 对照 RB 脚本修正（RB 正常） |
| J | 近远月价差（1个）| J1 futures_main_sina 返回空，需换接口 |

> **进展 2026-05-06**：PB_POS_NET 已修复 ✅。剩余 PB 仓单/基差/月差 + PP/Y/HC 待 mimo 逐品种修复（上次任务过大导致超时，已拆分小批次重派）。

### R3 🔲 待执行 — 编写缺失的免费因子爬虫（EC/LC/LH/SC/SN）

| 品种 | 新增脚本数 | AKShare 接口 |
|------|-----------|-------------|
| SC | 8个 | `eia_crude_stock`, `futures_foreign`, OPEC scraping, `futures_spot`, `fx_spot_quote` 等 |
| EC | 6个 | `scfi_index`, `futures_basis`, `futures_spread`, `ine_position_rank` |
| SN | 5个 | `futures_spot`, `futures_foreign`, `futures_spread`, `shfe_warrant` |
| LH | 5个 | `hog_price`, `futures_spot`, `futures_basis` |
| LC | 4个 | `energy_index`, `futures_spot`, `futures_basis`, `macro_china` |

策略：参考已有品种（CU/AG/AU）的脚本模板，复用 AKShare 接口。预估总工时 15-20h。

### R4 🔲 待预算决策 — 订阅关键付费数据源

| 数据源 | 解锁因子数 | 覆盖品种 |
|--------|-----------|---------|
| SMM | ~15个 | PB/PP/Y/HC/SN/LC |
| 隆众资讯（能化）| ~12个 | PP/Y/HC/SC/J |
| 卓创资讯 | ~10个 | PP/Y/PB/HC |
| 汾渭能源 | ~5个 | J |
| Mysteel 深度 | ~8个 | HC/I/PB/J |

**建议**：优先 SMM（覆盖面最广，15个因子分布在6品种），其次隆众（能化品种覆盖全）。

### 修复后预期

| 阶段 | 动作 | 预期效果 |
|------|------|---------|
| R1 ✅ | 修置信度 | J 5×1→5×N，全部品种解除阻塞 |
| R2 🔄 | 修免费API | PB 2→6, PP 2→5, HC 3→7 |
| R3 | 写免费脚本 | SC 2→10, EC 2→8, SN 3→8, LH 2→7, LC 2→6 |
| R4 | 订阅付费源 | 补齐剩余 ~45 因子，全面上线 |

---

## 六、执行顺序

1. **B类统一排查**（收益最大）：PB → PP → Y → HC → J，修后每品种新增 3-5 个因子
2. **A类按重要性补采**：SC（大宗之王）→ EC → LC → LH
3. **C类补缺**：SN → I → P
4. **R4 预算提交**：SMM > 隆众 > 其他

---

## 七、关键发现（方法论层面）

1. **"脚本在但数据空"不是bug，是功能**：系统为付费因子预留了骨架脚本，付费后立即可采集。这个设计是对的——问题在于没人意识到付费占比这么高。

2. **`save_to_db` 的置信度匹配缺少 pub_date 维度**：已修复。同 obs_date 不同 pub_date 的记录现在可以共存。

3. **SC（原油）是最大浪费**：EIA库存、OPEC产量、美国产量、DXY、裂解价差——所有核心因子都是完全免费公开数据，SC 从 2→10 因子只需写 8 个 AKShare 脚本。

4. **品种间数据源共享被忽视了**：SHFE 仓单/持仓 API 对 CU/RU 一次验证通过，PB/HC 却没复用同一套代码。品种间应建立共享的"数据源连接器"模式。

---

*报告结束 | 已完成：R1 ✅ + PB_POS_NET ✅ | 进行中：R2 按品种拆分重派 mimo | 待执行：R3（15-20h）+ R4（待预算）*
