#!/usr/bin/env python3
"""
YAML 语义验证工具
扫描 futures_v6/macro_engine/config 下的因子和品种配置文件，
检查类型、必需字段、合理范围。
只读+报告，不修改任何文件。
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any, Optional

import yaml

# ── 配置 ────────────────────────────────────────────────────────────────────

FACTORS_DIR = Path(r"D:\futures_v6\macro_engine\config\factors")
INSTRUMENTS_DIR = Path(r"D:\futures_v6\macro_engine\config\instruments")

VALID_CATEGORIES = {
    "free_data",
    "paid_data",
    "derived",
    "model_signal",
    "alternative_data",
    "technical",
    "macro",
}

REQUIRED_FIELDS = {
    "factor_code",
    "name",
    "category",
    "description",
    "data_source",
    "source_confidence",
}

# ── 辅助函数 ────────────────────────────────────────────────────────────────


# No custom comment stripping needed — yaml.safe_load handles inline comments correctly.


def _parse_expected_range(raw: Any, filename: str, field_path: str) -> tuple[list, list[str]]:
    """
    解析 expected_range 字段。
    接受:
      - [num, num]          → YAML 原生列表
      - "[num, num]"         → 带引号字符串
      - "num, num"           → 无括号字符串
    返回 (parsed_list, errors)
    """
    errors: list[str] = []

    if raw is None:
        return [], ["expected_range: field is null"]

    # 情况1：YAML 原生列表 / 元组
    if isinstance(raw, (list, tuple)):
        values = list(raw)
        if len(values) != 2:
            return values, [f"expected_range: expected exactly 2 elements, got {len(values)}"]
        parsed = []
        for i, v in enumerate(values):
            try:
                parsed.append(float(v))
            except (TypeError, ValueError):
                return values, [f"expected_range: element[{i}] cannot be converted to float: {v!r}"]
        return parsed, []

    # 情况2：字符串
    if isinstance(raw, str):
        # 去掉引号
        s = raw.strip().strip("'\"").strip()
        # 支持 "[num, num]" 或 "num, num"
        s = re.sub(r"^\[|\]$", "", s).strip()
        parts = re.split(r",\s*", s)
        if len(parts) != 2:
            return [], [f"expected_range: string format 'num, num' parsed {len(parts)} elements: {raw!r}"]
        try:
            parsed = [float(parts[0]), float(parts[1])]
            return parsed, []
        except ValueError as e:
            return [], [f"expected_range: string cannot be parsed as numbers: {raw!r} ({e})"]

    return [], [f"expected_range: expected list[float,float] or 'num,num' string, got {type(raw).__name__}: {raw!r}"]


def _validate_single_file(
    path: Path, is_instrument_file: bool
) -> list[str]:
    """
    验证单个 YAML 文件。
    返回错误列表（空=无错误）。
    """
    errors: list[str] = []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError as e:
        return [f"YAML 解析失败: {e}"]

    if data is None:
        return []  # 空文件跳过

    # ── 品种配置文件（instruments/*.yaml）───────────────
    if is_instrument_file:
        # _base.yaml / _templates.yaml 等模板文件跳过完整验证
        if path.name.startswith("_"):
            return errors

        # 验证 symbol 字段类型
        if "symbol" in data:
            if not isinstance(data["symbol"], str):
                errors.append(
                    f"symbol: 期望 str，实际 {type(data['symbol']).__name__}({data['symbol']!r})"
                )
        else:
            errors.append("symbol: missing required field")

        # 验证 name（中文名）
        if "name" in data:
            if not isinstance(data["name"], str):
                errors.append(
                    f"name: 期望 str，实际 {type(data['name']).__name__}({data['name']!r})"
                )
        else:
            errors.append("name: missing required field")

        # 验证 name_en
        if "name_en" in data:
            if not isinstance(data["name_en"], str):
                errors.append(
                    f"name_en: 期望 str，实际 {type(data['name_en']).__name__}({data['name_en']!r})"
                )

        # 验证 sector
        VALID_SECTORS = {"农产品", "黑色", "有色", "能化", "贵金属"}
        if "sector" in data:
            if not isinstance(data["sector"], str):
                errors.append(
                    f"sector: 期望 str，实际 {type(data['sector']).__name__}({data['sector']!r})"
                )
            elif data["sector"] not in VALID_SECTORS:
                errors.append(
                    f"sector: value '{data['sector']}' not in known enum; expected: {', '.join(sorted(VALID_SECTORS))}"
                )
        else:
            errors.append("sector: missing required field")

        # 验证 macro_lambda
        if "macro_lambda" in data:
            ml = data["macro_lambda"]
            if not isinstance(ml, (int, float)):
                errors.append(
                    f"macro_lambda: 期望 float|int，实际 {type(ml).__name__}({ml!r})"
                )
            elif not (0.0 <= float(ml) <= 1.0):
                errors.append(f"macro_lambda: value {ml} out of range [0.0, 1.0]")
        # 验证 weights（字典，值为数字）
        if "weights" in data:
            w = data["weights"]
            if not isinstance(w, dict):
                errors.append(f"weights: 期望 dict，实际 {type(w).__name__}")
            else:
                for k, v in w.items():
                    if not isinstance(v, (int, float)):
                        errors.append(
                            f"weights.{k}: 期望 float|int，实际 {type(v).__name__}({v!r})"
                        )
        return errors

    # ── 因子配置文件（factors/*/*.yaml）───────────────
    # 检查必需字段
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{field}: missing required field")

    # factor_code 类型
    if "factor_code" in data:
        val = data["factor_code"]
        if not isinstance(val, str):
            errors.append(
                f"factor_code: 期望 str，实际 {type(val).__name__}({val!r})"
            )

    # category 枚举
    if "category" in data:
        val = data["category"]
        if not isinstance(val, str):
            errors.append(
                f"category: 期望 str，实际 {type(val).__name__}({val!r})"
            )
        elif val not in VALID_CATEGORIES:
            errors.append(
                f"category: value '{val}' not in known enum; expected: {', '.join(sorted(VALID_CATEGORIES))}"
            )

    # source_confidence 类型 + 范围
    if "source_confidence" in data:
        val = data["source_confidence"]
        if isinstance(val, bool):  # bool 是 int 的子类，YAML 中 True/False 会被解析为 bool
            errors.append(
                f"source_confidence: 期望 float|int，实际 bool({val})"
            )
        elif not isinstance(val, (int, float)):
            errors.append(
                f"source_confidence: 期望 float|int，实际 {type(val).__name__}({val!r})"
            )
        else:
            if not (0.0 <= float(val) <= 5.0):
                errors.append(
                    f"source_confidence: value {val} out of range [0.0, 5.0]  # 整数评分: 1=低 2=中 3=高 4=很高 5=权威"
                )

    # expected_range 解析 + 验证
    if "expected_range" in data:
        parsed, parse_errors = _parse_expected_range(
            data["expected_range"], path.name, "expected_range"
        )
        errors.extend(parse_errors)
        if not parse_errors and len(parsed) == 2:
            if not (parsed[0] < parsed[1]):
                errors.append(
                    f"expected_range: element[0] ({parsed[0]}) must be < element[1] ({parsed[1]})"
                )

    return errors


# ── 主流程 ──────────────────────────────────────────────────────────────────


def main() -> int:
    all_files: list[Path] = []
    errors_map: dict[Path, list[str]] = {}

    # 扫描 factors/（递归，含子目录）
    if FACTORS_DIR.exists():
        for p in FACTORS_DIR.rglob("*.yaml"):
            if "_templates" in p.name:
                continue
            all_files.append(p)

    # 扫描 instruments/
    if INSTRUMENTS_DIR.exists():
        for p in INSTRUMENTS_DIR.glob("*.yaml"):
            if "_templates" in p.name:
                continue
            all_files.append(p)

    total = len(all_files)
    error_file_count = 0
    total_errors = 0

    for path in sorted(all_files, key=str):
        is_instrument = INSTRUMENTS_DIR in path.parents or path.parent == INSTRUMENTS_DIR
        errs = _validate_single_file(path, is_instrument_file=is_instrument)
        if errs:
            errors_map[path] = errs
            error_file_count += 1
            total_errors += len(errs)
            for e in errs:
                fname = path.name
                print(f"[X] [{fname}] {e}")

    # 摘要
    print()
    if total_errors == 0:
        print(f"[OK] All passed ({total} files)")
    else:
        print(f"[SUMMARY] Scanned {total} files | {error_file_count} files with errors | {total_errors} total errors")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
