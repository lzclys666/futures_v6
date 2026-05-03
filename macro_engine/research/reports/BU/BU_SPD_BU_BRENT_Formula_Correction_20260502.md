# BU_SPD_BU_BRENT 公式纠正备忘录

**日期**：2026-05-02
**问题**：沥青-原油价比（BU/Brent）直接除法存在单位+货币双重错误
**状态**：⚠️ 需修正，未修正前不得用于生产

---

## 一、错误公式（当前）

```
BU_SPD_BU_BRENT = BU_price_CNY_per_ton / Brent_price_CNY_per_bbl
```

或等价为：

```
BU_SPD_BU_BRENT = BU_price / SC_price
```

### ❌ 错误原因

| 问题 | 说明 |
|------|------|
| **单位量纲错误** | BU = 元/**吨**，SC/Brent = 元（或USD）/**桶**，吨 ≠ 桶，不可直接除 |
| **货币问题（如未处理）** | 若 Brent 原始数据为 USD/桶，还需 FX 汇率换算 |

---

## 二、正确公式（三步换算）

### Step 1：统一原油端货币（USD → CNY）

若 Brent 原始数据为 USD/桶，需换算：
```
Brent_CNY_per_bbl = Brent_USD_per_bbl × USD_CNY汇率
```
> 若数据源已是 CNY/桶（如 SC 原油期货），跳过此步。

### Step 2：统一沥青端单位（吨 → 桶）

沥青与原油的标准桶/吨换算系数（期货合约规格）：
```
换算系数 ≈ 7.3 ~ 7.5 桶/吨
```
- 沥青密度约 1.0~1.05 g/cm³（70号道路沥青）
- 上海国际能源交易中心（INE）SC 合约：1吨 ≈ 7.35 桶（参考值，以交易所规格为准）
- BU 合约乘数：1手 = 10吨

```
BU_CNY_per_bbl = BU_CNY_per_ton / CONV_factor
```

### Step 3：计算比价（正确公式）

```
BU_SPD_BU_BRENT = BU_CNY_per_ton / (Brent_CNY_per_bbl × CONV_factor)
```

或等价形式（统一到 CNY/桶）：
```
= BU_CNY_per_ton / CONV_factor   vs   Brent_CNY_per_bbl
```

---

## 三、完整公式（Python 表示）

```python
# 参数
CONV_BU_TO_BBL = 7.35  # 桶/吨换算系数（需确认交易所最新规格）

def correct_bu_spd_bu_brent(
    bu_cny_per_ton: float,       # BU沥青期货，元/吨
    brent_cny_per_bbl: float,   # Brent原油，元/桶（如用SC则是CNY/桶）
    usd_cny_fx: float = None    # 可选：USD/CNY汇率（如brent原始数据为USD/桶）
) -> float:
    if usd_cny_fx is not None:
        brent_cny_per_bbl = brent_cny_per_bbl * usd_cny_fx
    bu_cny_per_bbl = bu_cny_per_ton / CONV_BU_TO_BBL
    return bu_cny_per_bbl / brent_cny_per_bbl
```

---

## 四、经济含义

| 指标 | 含义 |
|------|------|
| BU_SPD_BU_BRENT **上升** | 沥青相对原油走强（炼厂增产焦化/沥青路线竞争 or 道路需求旺盛） |
| BU_SPD_BU_BRENT **下降** | 沥青相对原油走弱（原油成本抬升 or 道路需求萎缩） |

> **注意**：BU与Brent价格比不是简单的大宗商品比价，而是反映炼厂行为（转产动机）和道路需求周期的综合指标。

---

## 五、待确认事项

- [ ] BU合约桶/吨换算系数需查上期所最新规格（CONV_BU_TO_BBL）
- [ ] Brent数据源：是直接用ICE Brent USD/桶再FX转换，还是用SC（CNY/桶）作为原油代理？
- [ ] 确认FX汇率使用即期 USD/CNY（CNH）还是USD/CNY中间价

---

## 六、涉及文件

- 原始定义：`BU_crawler_delivery_20260419.md`（第二梯队因子 #2：沥青-原油价比）
- 本纠正文档：`BU_SPD_BU_BRENT_Formula_Correction_20260502.md`
