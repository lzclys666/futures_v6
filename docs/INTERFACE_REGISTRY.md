# 接口注册表 — INTERFACE_REGISTRY

> 版本：1.0 | 更新：2026-04-22 | 状态：锁定

---

## 接口总览

| 接口ID | 类型 | 路径 | 描述 | 状态 |
|--------|------|------|------|------|
| I001 | 数据提供器 | `DataProvider` | 抽象基类，定义因子数据获取接口 | 🔒 锁定 |
| I002 | 标准化器 | `Normalizer` | 抽象基类，定义因子标准化接口 | 🔒 锁定 |
| I003 | 权重计算器 | `WeightCalculator` | 抽象基类，定义动态权重接口 | 🔒 锁定 |
| I004 | 流水线节点 | `PipelineNode` | 抽象基类，定义 Pipeline 节点接口 | 🔒 锁定 |
| I005 | 状态检测器 | `RegimeDetector` | 抽象基类，定义市场状态识别接口 | 🔒 锁定 |

---

## I001 — DataProvider（数据提供器）

**文件：** `core/interfaces.py`  
**状态：** 🔒 锁定  
**版本：** 1.0

### 接口签名

```python
class DataProvider(ABC):
    @abstractmethod
    def fetch_factor(
        self,
        symbol: str,
        factor_name: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        获取指定品种在时间窗口内的因子值。

        Args:
            symbol:      品种代码，如 "RU"
            factor_name: 因子名称，如 "PMI"
            start_date:  窗口起始日期（PIT 观察日）
            end_date:    窗口结束日期（PIT 观察日）

        Returns:
            DataFrame，列：[obs_date, pub_date, value]
            - obs_date:  观察日（Point-in-Time）
            - pub_date:  发布时间
            - value:     因子原始值

        Raises:
            DataNotFoundError: 数据不存在
            ValidationError:   参数校验失败
        """
        pass
```

### PIT 查询规则（强制）
- **必须同时过滤** `obs_date` 和 `pub_date`
- 不得省略任一过滤条件
- 不允许"前瞻偏差"——不得使用 `obs_date > pub_date` 的数据

### 字段规范

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `obs_date` | date | PIT 观察日 |
| `pub_date` | date | 数据发布日期 |
| `value` | float | 因子原始值，None 表示缺失 |

---

## I002 — Normalizer（标准化器）

**文件：** `core/interfaces.py`  
**状态：** 🔒 锁定  
**版本：** 1.0

### 接口签名

```python
class Normalizer(ABC):
    @abstractmethod
    def normalize(self, raw_series: pd.Series) -> pd.Series:
        """
        对原始因子序列进行标准化。

        Args:
            raw_series: 原始因子值序列，index 为 obs_date

        Returns:
            标准化后序列，与输入等长，index 相同
            - 中位数对齐
            - MAD 缩放
            - 截断至 ±3 MAD

        Raises:
            ValueError:  输入长度不足窗口要求
        """
        pass

    @abstractmethod
    def get_params(self) -> dict:
        """返回当前使用的标准化参数（窗口、中位数、MAD 等）。"""
        pass
```

### 标准化规则（强制）
- 使用 **MAD（中位数绝对偏差）** 缩放
- 中位数对齐：先减中位数，再除以 MAD
- MAD=0 时返回全零序列（不得抛出除零异常）
- 截断阈值：±3 MAD（硬截断）

---

## I003 — WeightCalculator（权重计算器）

**文件：** `core/interfaces.py`  
**状态：** 🔒 锁定  
**版本：** 1.0

### 接口签名

```python
class WeightCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        factor_ic_series: pd.Series,
        regime: str,
    ) -> pd.Series:
        """
        根据因子 IC 序列和市场状态计算动态权重。

        Args:
            factor_ic_series: 因子 IC 序列，index 为 obs_date
            regime:            当前市场状态，"BULL" | "BEAR" | "NEUTRAL"

        Returns:
            权重序列，index 与输入相同，所有权重之和为 1

        Raises:
            ValueError: regime 无效
        """
        pass

    @abstractmethod
    def get_params(self) -> dict:
        """返回当前权重计算参数。"""
        pass
```

### 权重计算规则（强制）
- 四维校准：IC 方向、IC 幅度、IC 持续性、IC 稳定性
- 收缩估计：防止极端权重过拟合
- 状态自适应：不同 regime 使用不同 IC 阈值
- 权重归一化：所有权重之和严格等于 1

---

## I004 — PipelineNode（流水线节点）

**文件：** `core/interfaces.py`  
**状态：** 🔒 锁定  
**版本：** 1.0

### 接口签名

```python
class PipelineNode(ABC):
    @abstractmethod
    def execute(self, data: dict) -> dict:
        """
        执行节点逻辑。

        Args:
            data: 上游传递的 data dict，至少包含：
                  - symbol: str
                  - factor_data: pd.DataFrame
                  - obs_date: date
                  - pub_date: date

        Returns:
            更新后的 data dict，携带本节点产出字段
            节点不得删除上游字段，只能新增

        Raises:
            PipelineError: 节点执行失败
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """节点名称，全局唯一。"""
        pass

    @property
    def dependencies(self) -> list[str]:
        """依赖的上游节点名称列表。默认无依赖。"""
        return []
```

### Pipeline 节点规范（强制）
- 品种差异通过**配置注入**，节点内不得硬编码品种逻辑
- data dict 字段不得删除，只能新增
- 节点名称全局唯一
- 执行失败应抛出 `PipelineError`，不得静默吞异常

---

## I005 — RegimeDetector（市场状态检测器）

**文件：** `core/interfaces.py`  
**状态：** 🔒 锁定  
**版本：** 1.0

### 接口签名

```python
class RegimeDetector(ABC):
    @abstractmethod
    def detect(self, price_series: pd.Series) -> str:
        """
        根据价格序列识别当前市场状态。

        Args:
            price_series: 价格序列，index 为日期

        Returns:
            市场状态字符串：
            - "BULL":   趋势向上
            - "BEAR":   趋势向下
            - "NEUTRAL":趋势不明或震荡

        Raises:
            ValueError: 输入长度不足
        """
        pass

    @abstractmethod
    def get_regime_params(self) -> dict:
        """返回当前检测器参数（窗口、阈值等）。"""
        pass
```

### 状态检测规则（强制）
- 使用 **HP 滤波**（月频）分解趋势
- 仅支持月频数据
- 三态输出：BULL / BEAR / NEUTRAL
- 状态切换需平滑（避免频繁跳动）

---

## 变更记录

| 日期 | 接口ID | 变更类型 | 描述 |
|------|--------|----------|------|
| 2026-04-22 | 全部 | 初始锁定 | 初始版本，I001-I005 接口冻结 |
