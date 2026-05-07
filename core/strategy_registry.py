# core/strategy_registry.py
"""
策略注册中心 — 自动发现 + YAML 绑定 + 热加载

功能：
1. 扫描 strategies/ 目录，动态 import，发现 CtaTemplate 子类
2. 读取 config/strategy_bindings.yaml，绑定品种→策略
3. 监听 YAML 文件变化，热加载绑定配置
4. 提供查询接口供 run.py 和 API 使用

用法：
    from core.strategy_registry import StrategyRegistry
    registry = StrategyRegistry(strategy_dir, bindings_path)
    registry.discover()  # 发现策略类
    bindings = registry.get_bindings()  # 获取品种→策略绑定
"""

import importlib
import importlib.util
import inspect
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

logger = logging.getLogger("StrategyRegistry")


class StrategyInfo:
    """策略元数据"""

    def __init__(self, cls: Type, module_path: Path, name: str = "", author: str = ""):
        self.cls = cls
        self.module_path = module_path
        self.name = name or cls.__name__
        self.author = author or getattr(cls, "author", "unknown")
        self.class_name = cls.__name__
        self.params = getattr(cls, "parameters", [])
        self.variables = getattr(cls, "variables", [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class_name": self.class_name,
            "author": self.author,
            "module": str(self.module_path),
            "params": self.params,
            "variables": self.variables,
        }


class StrategyRegistry:
    """
    策略注册中心

    职责：
    - discover(): 扫描策略目录，发现 CtaTemplate 子类
    - load_bindings(): 读取 YAML 绑定配置
    - get_bindings(): 返回 {vt_symbol: {strategy, params, enabled}}
    - get_strategy_class(name): 按名称获取策略类
    - check_reload(): 检测 YAML 文件变化，热加载
    """

    def __init__(
        self,
        strategy_dir: Path,
        bindings_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ):
        self.strategy_dir = Path(strategy_dir)
        self.bindings_path = bindings_path or Path("config/strategy_bindings.yaml")
        self.project_dir = project_dir or Path.cwd()

        # 策略类注册表 {class_name: StrategyInfo}
        self._strategies: Dict[str, StrategyInfo] = {}
        # 品种绑定 {vt_symbol: {strategy, params, enabled}}
        self._bindings: Dict[str, Dict[str, Any]] = {}
        # 默认参数
        self._defaults: Dict[str, Any] = {}
        # YAML 文件 mtime（热加载检测）
        self._bindings_mtime: float = 0.0

    # ==================== 策略发现 ====================

    def discover(self) -> int:
        """
        扫描 strategy_dir，动态导入所有 .py 文件，找出 CtaTemplate 子类。

        Returns:
            int: 发现的策略类数量
        """
        if not self.strategy_dir.exists():
            logger.warning("策略目录不存在: %s", self.strategy_dir)
            return 0

        # 确保 strategy_dir 在 sys.path 中
        strategy_dir_str = str(self.strategy_dir)
        if strategy_dir_str not in sys.path:
            sys.path.insert(0, strategy_dir_str)

        count = 0
        for py_file in sorted(self.strategy_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                classes = self._load_module_classes(py_file)
                for cls_name, cls in classes.items():
                    if cls_name in self._strategies:
                        continue
                    info = StrategyInfo(cls=cls, module_path=py_file)
                    self._strategies[cls_name] = info
                    count += 1
                    logger.info("发现策略: %s (from %s)", cls_name, py_file.name)
            except Exception as e:
                logger.warning("加载策略文件失败 %s: %s", py_file.name, e)

        logger.info("策略发现完成: %d 个策略类", count)
        return count

    def _load_module_classes(self, py_file: Path) -> Dict[str, Type]:
        """动态导入 .py 文件，返回其中的 CtaTemplate 子类"""
        module_name = f"strategy_{py_file.stem}"

        # 如果模块已加载，先删除（支持重新加载）
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, str(py_file))
        if spec is None or spec.loader is None:
            return {}

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 找出 CtaTemplate 子类
        try:
            from vnpy_ctastrategy import CtaTemplate
        except ImportError:
            logger.warning("vnpy_ctastrategy 未安装，无法检测 CtaTemplate 子类")
            return {}

        classes = {}
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, CtaTemplate)
                and obj is not CtaTemplate
                and not name.startswith("_")
            ):
                classes[name] = obj
        return classes

    # ==================== 绑定配置 ====================

    def load_bindings(self) -> bool:
        """
        读取 strategy_bindings.yaml。

        Returns:
            bool: 是否加载成功
        """
        if not self.bindings_path.exists():
            logger.warning("绑定配置不存在: %s", self.bindings_path)
            return False

        try:
            with open(self.bindings_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)

            if not cfg:
                logger.warning("绑定配置为空")
                return False

            self._defaults = cfg.get("defaults", {})
            raw_bindings = cfg.get("bindings", {})

            bindings = {}
            for vt_symbol, entry in raw_bindings.items():
                if not isinstance(entry, dict):
                    continue
                strategy_name = entry.get("strategy", "")
                params = entry.get("params", {})
                enabled = entry.get("enabled", True)

                # 合并默认参数
                merged_params = {**self._defaults, **params}

                bindings[vt_symbol] = {
                    "strategy": strategy_name,
                    "params": merged_params,
                    "enabled": enabled,
                }

            self._bindings = bindings
            self._bindings_mtime = self.bindings_path.stat().st_mtime
            logger.info(
                "绑定配置已加载: %d 个品种 (%d 启用)",
                len(bindings),
                sum(1 for b in bindings.values() if b["enabled"]),
            )
            return True

        except Exception as e:
            logger.error("加载绑定配置失败: %s", e)
            return False

    def check_reload(self) -> bool:
        """
        检测绑定配置文件是否变化，如变化则重新加载。

        Returns:
            bool: 是否发生了重新加载
        """
        try:
            if not self.bindings_path.exists():
                return False
            current_mtime = self.bindings_path.stat().st_mtime
            if current_mtime <= self._bindings_mtime:
                return False
            logger.info("检测到绑定配置变更，重新加载...")
            return self.load_bindings()
        except Exception as e:
            logger.warning("检查绑定配置变化失败: %s", e)
            return False

    # ==================== 查询接口 ====================

    def get_bindings(self) -> Dict[str, Dict[str, Any]]:
        """返回品种→策略绑定（只读副本）"""
        return dict(self._bindings)

    def get_enabled_bindings(self) -> Dict[str, Dict[str, Any]]:
        """返回仅启用的绑定"""
        return {k: v for k, v in self._bindings.items() if v.get("enabled")}

    def get_strategy_class(self, class_name: str) -> Optional[Type]:
        """按类名获取策略类"""
        info = self._strategies.get(class_name)
        return info.cls if info else None

    def get_strategy_info(self, class_name: str) -> Optional[StrategyInfo]:
        """按类名获取策略元数据"""
        return self._strategies.get(class_name)

    def get_all_strategies(self) -> Dict[str, StrategyInfo]:
        """返回所有已发现的策略"""
        return dict(self._strategies)

    def list_strategies(self) -> List[Dict[str, Any]]:
        """返回策略列表（可序列化，供 API 使用）"""
        return [info.to_dict() for info in self._strategies.values()]

    def validate_bindings(self) -> List[str]:
        """
        校验绑定配置：引用的策略类是否都已发现。

        Returns:
            List[str]: 错误信息列表（空=全部通过）
        """
        errors = []
        for vt_symbol, binding in self._bindings.items():
            strategy_name = binding.get("strategy", "")
            if strategy_name not in self._strategies:
                errors.append(
                    f"{vt_symbol}: 策略类 '{strategy_name}' 未在 strategies/ 中发现"
                )
        return errors


# ==================== 全局单例 ====================
_registry_instance: Optional[StrategyRegistry] = None


def get_registry() -> Optional[StrategyRegistry]:
    """获取全局注册中心实例"""
    return _registry_instance


def init_registry(
    strategy_dir: Path,
    bindings_path: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> StrategyRegistry:
    """初始化全局注册中心"""
    global _registry_instance
    _registry_instance = StrategyRegistry(
        strategy_dir=strategy_dir,
        bindings_path=bindings_path,
        project_dir=project_dir,
    )
    _registry_instance.discover()
    _registry_instance.load_bindings()
    errors = _registry_instance.validate_bindings()
    if errors:
        for err in errors:
            logger.warning("绑定校验: %s", err)
    return _registry_instance
