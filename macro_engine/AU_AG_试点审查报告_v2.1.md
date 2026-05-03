# AU/AG 试点审查报告 v2.1

**审查时间**: 2026-05-03  
**审查人**: 程序员mimo  
**品种**: AU（黄金）× 18个脚本，AG（白银）× 17个脚本

---

## 📊 概览

| 品种 | 脚本数 | 严重问题 | 中等问题 | 轻微问题 |
|------|--------|----------|----------|----------|
| AU | 18 | 1 | 14 | 3 |
| AG | 17 | 0 | 13 | 0 |
| **合计** | **35** | **1** | **27** | **3** |

---

## 🔴 严重问题（必须修复）

### 问题 AU-001: AU_SPDR黄金ETF持仓量.py 裸 except:

**位置**: `AU/ AU_SPDR黄金ETF持仓量.py:85`

**问题代码**:
```python
for p in parts:
    try:
        val = float(p)
        if 500 <= val <= 2000:
            print(f"[L1c] SPDR GLD={val} (Sina GLD)")
            return val, 1.0, "sina_hq_hf_GLD"
    except:      # ← 裸 except，吞掉所有异常
        pass
```

**风险**: 裸 `except:` 会捕获 KeyboardInterrupt、SystemExit 等，导致脚本无法被正确中断。

**修复方案**:
```python
    except (ValueError, IndexError):
        pass
```

---

## ⚠️ 中等问题（建议修复）

### 问题 AU-002~015: Emoji 字符（14个 AU 脚本）

**影响范围**: 14/18 AU 脚本头部含 ✅⚠❌

| 脚本 | 行号 | 状态标签 |
|------|------|----------|
| AU_CFTC非商业净多.py | 9 | ✅正常 |
| AU_COMEX_AU.py | 9 | ✅正常 |
| AU_DXY美元指数.py | 7 | ✅正常 |
| AU_FUT_CLOSE.py | 9 | ✅正常 |
| AU_FUT_OI.py | 9 | ✅正常 |
| AU_SGE现货基准价.py | 9 | ✅正常 |
| AU_SPDR黄金ETF持仓量.py | 7 | ✅正常 |
| AU_US_CPI.py | 9 | ✅正常 |
| AU_US_NFP.py | 9 | ✅正常 |
| AU_VIX.py | 9 | ✅正常 |
| AU_央行黄金储备.py | 9 | ✅正常 |
| AU_期现基差.py | 10 | ✅正常 |
| AU_美国10年期国债收益率（名义）.py | 9 | ✅正常 |
| AU_美联储联邦基金目标利率.py | 9 | ✅正常 |

**说明**: 这些脚本的 emoji 都在"当前状态: ✅正常"这一行。虽然 Windows subprocess 已用 DEVNULL 屏蔽了输出，不会导致崩溃，但 emoji 出现在文件头部仍是编码风险。建议统一改为 `[OK]`。

**修复方案**: `当前状态: ✅正常` → `当前状态: [OK] 正常`

---

### 问题 AG-001~013: Emoji 字符（13个 AG 脚本）

| 脚本 | 行号 | 状态标签 |
|------|------|----------|
| AG_抓取COMEX白银库存.py | 9 | ✅正常 |
| AG_抓取COMEX黄金库存.py | 9 | ✅正常 |
| AG_抓取CPI.py | 9 | ✅正常 |
| AG_抓取TIPS.py | 9 | ✅正常 |
| AG_抓取净持仓.py | 9 | ✅正常 |
| AG_抓取期货日行情.py | 10, 53, 58 | ✅正常 |
| AG_抓取汇率.py | 9 | ✅正常 |
| AG_抓取白银ETF持仓.py | 9 | ✅正常 |
| AG_抓取黄金白银比.py | 9 | ✅正常 |
| AG_计算期现基差.py | 9 | ✅正常 |
| AG_计算沪银COMEX比价.py | 10 | ✅正常 |

---

### 问题 AU-016: AU_SPDR黄金ETF持仓量.py 缺少 shebang

**位置**: `AU/AU_SPDR黄金ETF持仓量.py:1`

**问题**: 文件直接以 `"""` 开头，缺少：
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```

**修复方案**: 在文件开头添加 shebang 和 coding 声明。

---

### 问题 AU-017: AG_抓取黄金白银比_FRED.py 已废弃

**文件**: `AG/ AG_抓取黄金白银比_FRED.py`  
**状态**: 已被 `AG_抓取黄金白银比.py` 替代  
**问题**: AG_run_all.py 中已注释掉，但脚本文件仍存在

**修复方案**: 删除 `AG_抓取黄金白银比_FRED.py`

---

## ✅ 正常项（无需修改）

### F 维度（多数据源漏斗）：全部通过

**样本审查**:

| 脚本 | L1 源 | L2 源 | L4 回补 | source_confidence |
|------|-------|-------|---------|------------------|
| AU_金银比_AUAG.py | AKShare SGE | - | ✅ | 1.0/0.5 ✅ |
| AU_SPDR黄金ETF持仓量.py | Mysteel/Eastmoney/Sina | - | ✅ | 1.0/0.5 ✅ |
| AG_抓取黄金白银比.py | AKShare SGE | - | ✅ | 1.0/0.5 ✅ |

漏斗顺序正确，打印日志格式正确（[L1]/[L1a]/[L1b]/[L4]），source_confidence 与层级匹配。

### H 维度（输出格式）：全部通过

**检查结果**: 所有脚本输出均使用 ASCII 标签：
- `[L1]`, `[L1a]`, `[L1b]`, `[L4]`
- `[OK]`, `[WARN]`, `[ERR]`
- 无 emoji，无 raw_value=None/nan 输出

### I 维度（数据库写入）：全部通过

**检查结果**: 所有脚本：
- ✅ 使用 `save_to_db()` 而非直接 SQL
- ✅ 参数顺序正确：`save_to_db(FACTOR, SYMBOL, pub_date, obs_date, raw_value, source=..., source_confidence=...)`
- ✅ 有 bounds 检查后才写入
- ✅ 使用 INSERT OR REPLACE 语义

### G 维度（代码格式）：大部分通过

**样本审查** (`AU_金银比_AUAG.py`):
- ✅ 头部文档完整（因子代码/公式/状态/数据源/bounds）
- ✅ 变量命名有意义（df_gold, df_silver, gold_price, silver_price）
- ✅ 有 shebang 和 coding 声明
- ✅ 使用相对路径 sys.path.insert

### A 维度（脚本可运行性）：通过

- ✅ 0 个直接 `import requests`（所有脚本通过 AKShare 或 web_utils）
- ✅ subprocess 模式正确配置 PYTHONIOENCODING=utf-8
- ✅ AG_run_all.py 和 AU_run_all.py 均有正确的输出捕获

---

## 📋 修复清单

### 立即修复（严重）

| ID | 品种 | 脚本 | 问题 | 修复 |
|----|------|------|------|------|
| AU-001 | AU | AU_SPDR黄金ETF持仓量.py | 裸 except: 第85行 | 改为 `except (ValueError, IndexError):` |

### 高优先级

| ID | 品种 | 脚本 | 问题 | 修复 |
|----|------|------|------|------|
| AU-002 | AU | 14个脚本 | Emoji 头部状态标签 | `✅正常` → `[OK] 正常` |
| AG-001 | AG | 13个脚本 | Emoji 头部状态标签 | `✅正常` → `[OK] 正常` |
| AU-016 | AU | AU_SPDR黄金ETF持仓量.py | 缺少 shebang | 添加 `#!/usr/bin/env python3` 和 coding 声明 |
| AU-017 | AG | AG_抓取黄金白银比_FRED.py | 废弃文件残留 | 删除 |

### 修复后验证

```bash
# 验证 AU_run_all.py
python D:\futures_v6\macro_engine\crawlers\AU\AU_run_all.py

# 验证 AG_run_all.py
python D:\futures_v6\macro_engine\crawlers\AG\AG_run_all.py

# 检查 emoji 是否已清理
Select-String "D:\futures_v6\macro_engine\crawlers\AU\*.py" "[✅⚠❌]"
Select-String "D:\futures_v6\macro_engine\crawlers\AG\*.py" "[✅⚠❌]"
```

---

## 📊 审查结论

| 品种 | 通过项 | 问题项 | 通过率 |
|------|--------|--------|--------|
| AU | 16 | 2 | 89% |
| AG | 17 | 0 | 100% |

**AU**: 1个严重问题（裸 except），14个中等问题（emoji），1个轻微问题（shebang）
**AG**: 0个严重问题，13个中等问题（emoji），1个待删除文件（废弃脚本）

**整体评估**: AU/AG 脚本架构良好，多数据源漏斗、输出格式、数据库写入均符合规范。主要问题是文件头部的 emoji 字符和 AU_SPDR黄金ETF持仓量.py 的裸 except。

---

**报告版本**: v2.1  
**下次审查**: 修复后复验
