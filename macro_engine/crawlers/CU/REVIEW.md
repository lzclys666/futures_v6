# CU 因子采集脚本复查报告

**复查时间**: 2026-05-02 09:25 GMT+8
**复查人**: mimo
**工作目录**: `D:\futures_v6\macro_engine\crawlers\CU\`

---

## 一、范式检查汇总

| 脚本 | Docstring | try-except | timeout | 魔法数字 | 类型注解 | 日志 | CSV输出 | 中文路径 | 中断恢复 |
|------|-----------|------------|---------|---------|---------|------|---------|---------|---------|
| CU_run_all.py | ✅ | ✅ | N/A | ✅ | ❌ | ✅ | N/A | N/A | N/A |
| CU_抓取LME库存.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |
| CU_抓取SHFE仓单.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |
| CU_抓取库存.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L1/L2/L4 |
| CU_抓取持仓排名.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |
| CU_抓取期货持仓量.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |
| CU_沪铜期货库存.py | ⚠️ | ✅ | ❌ | ⚠️ | ❌ | ✅ | ✅ | ❌ | ✅ L4 |
| CU_计算基差.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |
| CU_计算近远月价差.py | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ L4 |

**共性问题**:
- ❌ 无一脚本设置 AKShare 网络请求 timeout（潜在无限等待风险）
- ❌ 所有脚本均无函数/方法类型注解
- ✅ 数据直接写 db（`save_to_db`），无 CSV 输出需求检查（`output\` 目录在范式中被要求但实际不需要）

---

## 二、逐脚本详细检查

### 2.1 CU_run_all.py

**范式符合度**: 🔧 轻微问题

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有 |
| try-except | ✅ subprocess 调用在 run_script 函数内 |
| 魔法数字 | ✅ BATCH1/BATCH2 常量 |
| 类型注解 | ❌ 无 |
| 日志 | ✅ print 输出 |
| CSV 输出 | N/A |
| 中文文件名 | N/A |

**问题**:
- `run_script` 函数无类型注解
- `subprocess.run` 传入 `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`，导致子脚本输出被吞掉，无法在父进程看到日志；建议改为捕获并打印

---

### 2.2 CU_抓取LME库存.py

**范式符合度**: ⚠️ 轻微问题

**运行结果** (2026-05-02): ✅ 成功
```
[DB] 写入成功: CU_INV_LME = 399725.0
[OK] CU_INV_LME=399725.0 obs=2026-04-30
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但内容"需补充"（Header不完整） |
| try-except | ✅ `except Exception as e` |
| timeout | ❌ `ak.macro_euro_lme_stock()` 无 timeout |
| 魔法数字 | ✅ EXPECTED_MIN=100000, EXPECTED_MAX=800000 |
| 类型注解 | ❌ `fetch()` 无返回值类型注解 |
| 日志 | ✅ [L1 FAIL] / [L4 Fallback] / [OK] |
| CSV 输出 | ✅ 写 db |
| 中文路径 | ✅ |

**问题**:
- `pd` 在 `if __name__ == "__main__"` 块内导入，`fetch()` 函数内使用（运行时已导入，逻辑正确但不符合"顶部导入"规范）
- Header 状态仍为"⚠️待修复"且未填写"尝试过的数据源及结果"

---

### 2.3 CU_抓取SHFE仓单.py

**范式符合度**: ⚠️ 轻微问题

**运行结果** (2026-05-02): ✅ 成功
```
[DB] 写入成功: CU_WRT_SHFE = 60535.0
[OK] CU_WRT_SHFE=60535.0 obs=2025-05-15
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ `except Exception` |
| timeout | ❌ `ak.futures_shfe_warehouse_receipt()` 无 timeout |
| 魔法数字 | ✅ EXPECTED_MIN=5000, EXPECTED_MAX=200000 |
| 类型注解 | ❌ 多函数均无 |
| 日志 | ✅ [L1 FAIL] / [L4 Fallback] / [OK] |
| CSV 输出 | ✅ 写 db |
| 中文路径 | ✅ |

**问题**:
- obs_date 回退到 2025-05-15（旧数据），说明当前交易日无仓单数据，这是正确的 L4 行为，但说明搜索窗口可能需要扩大
- `get_wrt_from_cu_df` 中用 Unicode 编码 (`\u5b8c\u7a0d\u5546\u54c1\u603b\u8ba1`) 而非中文字符串，可读性差

---

### 2.4 CU_抓取库存.py

**范式符合度**: ✅ 良好

**运行结果** (2026-05-02): ✅ 成功
```
[DB] 写入成功: CU_INV_SHFE = 96664.0
[OK] CU_INV_SHFE=96664.0 obs=2026-04-30
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ L1 + L2 两层 fallback |
| timeout | ❌ 无 |
| 魔法数字 | ✅ EXPECTED_MIN/MAX |
| 类型注解 | ❌ |
| 日志 | ✅ [L1 FAIL] / [L2 FAIL] / [L4 Fallback] |
| CSV 输出 | ✅ 写 db |
| 中断恢复 | ✅ L1 → L2 → L4 三层漏斗 |

**问题**: `fetch()` 依赖外部 `pd` 导入（脚本底部 `import pandas as pd` 在 `if __name__` 块内）

---

### 2.5 CU_抓取持仓排名.py

**范式符合度**: ⚠️ 节假日失效

**运行结果** (2026-05-02, 节假日): ⚠️ L1失败，L4回补
```
[L1 FAIL] CU_POS_NET: SHFE CU持仓排名返回空 date=20260501
[L4 Fallback] CU_POS_NET=-25350.00
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ |
| timeout | ❌ 无 |
| 魔法数字 | ✅ EXPECTED_MIN=-200000, EXPECTED_MAX=200000 |
| 类型注解 | ❌ |
| 日志 | ✅ |
| 中断恢复 | ✅ L4 |

**问题**:
- `get_last_trading_day()` 只搜索最近30天，但2026-05-01是节假日（劳动节），AKShare 警告"20260501是节假日"，但实际脚本内没有跳过节假日的逻辑——`get_last_trading_day()` 只是找周一到周五，没有主动排除交易所公告的节假日
- `fetch()` 内对 AKShare 返回的 DataFrame 做 `.sum()` 运算，但没处理 NaN（`df['long_open_interest'].sum()` 默认忽略 NaN，可接受）

---

### 2.6 CU_抓取期货持仓量.py

**范式符合度**: ✅ 良好

**运行结果** (2026-05-02): ✅ 成功
```
[DB] 写入成功: CU_FUT_OI = 190887.0
[OK] CU_FUT_OI=190887.0 obs=2026-04-30
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ |
| timeout | ❌ 无 |
| 魔法数字 | ✅ |
| 类型注解 | ❌ |
| 日志 | ✅ |
| CSV 输出 | ✅ 写 db |

---

### 2.7 CU_沪铜期货库存.py

**范式符合度**: ❌ **严重错误**

**运行结果** (2026-05-02): ❌ 崩溃
```
NameError: name 'sys' is not defined
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ⚠️ 因子代码未填（"待定义"），状态"待修复" |
| try-except | ✅ |
| timeout | ❌ 无 |
| 魔法数字 | ⚠️ 使用短变量名 EMIN/EMAX/FCODE/SYM，可读性差 |
| 类型注解 | ❌ |
| 日志 | ✅ |
| 中文路径 | ❌ **hardcode 绝对路径** `d:/futures_v6/...` |
| 中断恢复 | ✅ L4 |
| if __name__ guard | ❌ **代码在模块级直接执行 sys.path.insert**，无 guard |

**严重问题**:
1. **`sys` 未 import**：`sys.path.insert(0, 'd:/futures_v6/...')` 在模块最顶层（line 17），但文件顶部没有 `import sys`
2. **hardcode 绝对路径**：与其他脚本使用 `os.path.join(this_dir, '..', 'common')` 的方式不一致，且路径是 Windows 专用格式
3. **`datetime.date.today()` 缺少 import**：`main()` 内调用 `datetime.date.today()`，但顶部没有 `import datetime`，会触发 `NameError`
4. **无 `if __name__ == "__main__"`**：脚本没有任何保护，任何 import 都会触发执行
5. **因子代码错误**：使用 `CU_DCE_INV`，而 README 中定义的因子代码不一致

---

### 2.8 CU_计算基差.py

**范式符合度**: ⚠️ 节假日失效

**运行结果** (2026-05-02, 节假日): ⚠️ L1失败，L4回补
```
[L1 FAIL] CU_SPD_BASIS: CU现货价返回空数据 date=20260501
[L4 Fallback] CU_SPD_BASIS=-293.33
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ |
| timeout | ❌ 无 |
| 魔法数字 | ✅ |
| 类型注解 | ❌ |
| 日志 | ✅ |

**问题**: 与 CU_抓取持仓排名.py 相同，`get_last_trading_day()` 不排除节假日

---

### 2.9 CU_计算近远月价差.py

**范式符合度**: ⚠️ 节假日失效

**运行结果** (2026-05-02, 节假日): ⚠️ L1失败，L4回补
```
[L1 FAIL] CU_SPD_CONTRACT: CU现货价返回空 date=20260501
[L4 Fallback] CU_SPD_CONTRACT=-140.0
```

| 检查项 | 结果 |
|--------|------|
| Docstring | ✅ 有，但"需补充" |
| try-except | ✅ |
| timeout | ❌ 无 |
| 魔法数字 | ✅ |
| 类型注解 | ❌ |
| 日志 | ✅ |

---

## 三、运行日志汇总

```
CU_抓取LME库存.py     ✅ CU_INV_LME=399725.0 obs=2026-04-30
CU_抓取库存.py        ✅ CU_INV_SHFE=96664.0 obs=2026-04-30
CU_抓取期货持仓量.py   ✅ CU_FUT_OI=190887.0 obs=2026-04-30
CU_抓取SHFE仓单.py    ✅ CU_WRT_SHFE=60535.0 obs=2025-05-15（历史数据）
CU_抓取持仓排名.py    ⚠️ L1失败(节假日) → L4回补: -25350.00
CU_计算基差.py        ⚠️ L1失败(节假日) → L4回补: -293.33
CU_计算近远月价差.py   ⚠️ L1失败(节假日) → L4回补: -140.0
CU_沪铜期货库存.py    ❌ NameError: sys 未定义（无法运行）
```

---

## 四、问题优先级

### P0 — 必须修复
1. **CU_沪铜期货库存.py**: `sys` 和 `datetime` 未 import，代码无法运行；hardcode 绝对路径需改为相对路径

### P1 — 建议修复
2. **所有脚本**: 为 AKShare 网络请求添加 `timeout=30` 参数
3. **所有脚本**: 添加函数类型注解（`def fetch() -> Tuple[float, date]`）

### P2 — 优化项
4. **CU_抓取持仓排名.py / CU_计算基差.py / CU_计算近远月价差.py**: `get_last_trading_day()` 函数需要识别节假日（考虑对接 `akshare` 的交易日历或硬编码2026年节假日列表）
5. **README.md**: 与实际脚本状态不符（CU_沪铜期货库存.py 标记为"⏸️stub"但实际是崩溃状态）

---

## 五、README.md 更新内容

```markdown
# CU — 铜 期货数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `CU` |
| 中文名称 | 铜 |
| 交易所 | SHFE |
| 合约代码 | CU |
| 品种分类 | 有色金属 |

## 因子配置

| 因子代码 | 描述 | 脚本 | 状态 |
|----------|------|------|------|
| CU_INV_SHFE | 沪铜库存 | CU_抓取库存.py | ✅ 正常 |
| CU_WRT_SHFE | SHFE仓单 | CU_抓取SHFE仓单.py | ✅ 正常 |
| CU_SPD_BASIS | 期现基差 | CU_计算基差.py | ⚠️ 节假日失效→L4回补 |
| CU_FUT_OI | 期货持仓量 | CU_抓取期货持仓量.py | ✅ 正常 |
| CU_POS_NET | 持仓净多 | CU_抓取持仓排名.py | ⚠️ 节假日失效→L4回补 |
| CU_INV_LME | LME库存 | CU_抓取LME库存.py | ✅ 正常 |
| CU_SPD_CONTRACT | 近远月价差 | CU_计算近远月价差.py | ⚠️ 节假日失效→L4回补 |
| CU_DCE_INV | 沪铜期货库存 | CU_沪铜期货库存.py | ❌ 崩溃(P0修复中) |

## 爬虫脚本

| 脚本 | 范式符合 | 运行状态 | 说明 |
|------|---------|---------|------|
| CU_run_all.py | 🔧 | ✅ | 调度入口，subprocess 输出被吞(建议优化) |
| CU_抓取LME库存.py | ⚠️ | ✅ | 缺timeout/类型注解 |
| CU_抓取SHFE仓单.py | ⚠️ | ✅ | 缺timeout/类型注解 |
| CU_抓取库存.py | ✅ | ✅ | L1/L2/L4三层漏斗，良好 |
| CU_抓取持仓排名.py | ⚠️ | ⚠️ | 节假日未处理→L4回补 |
| CU_抓取期货持仓量.py | ✅ | ✅ | 良好 |
| CU_沪铜期货库存.py | ❌ | ❌ | sys未import/硬编码路径/P0修复中 |
| CU_计算基差.py | ⚠️ | ⚠️ | 节假日未处理→L4回补 |
| CU_计算近远月价差.py | ⚠️ | ⚠️ | 节假日未处理→L4回补 |

## 运行方式

```bash
# 批量采集
python crawlers/CU/CU_run_all.py

# 单脚本测试
python crawlers/CU/<脚本名>.py
```

---
_复查时间: 2026-05-02 | 复查人: mimo_
```

---

## 六、交付结论

- **可正常运行**: 7/9 脚本（L4回补机制在节假日正常工作）
- **崩溃**: 1/9（CU_沪铜期货库存.py，P0优先级）
- **共性缺陷**: 无 timeout 设置，无类型注解，Header"待修复"状态未完成
- **建议**: CU_沪铜期货库存.py 需重写（修复 import + 路径 + if __name__ guard）
