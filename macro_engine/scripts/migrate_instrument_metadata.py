#!/usr/bin/env python3
"""
迁移脚本：为 instruments/*.yaml 补写 name/sector/name_en 字段
数据源：generate_all_symbols.py 中的 SYMBOL_CONFIGS
只修改有对应 SYMBOL_CONFIGS 条目的文件，不动 _base.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

INSTRUMENTS_DIR = Path(r"D:\futures_v6\macro_engine\config\instruments")

# ── 从 generate_all_symbols.py 提取的完整品种配置 ──
SYMBOL_CONFIGS = {
    "RU": {"name": "天然橡胶", "sector": "农产品"},
    "NR": {"name": "20号胶", "sector": "农产品"},
    "M":  {"name": "豆粕", "sector": "农产品"},
    "RM": {"name": "菜粕", "sector": "农产品"},
    "P":  {"name": "棕榈油", "sector": "农产品"},
    "Y":  {"name": "豆油", "sector": "农产品"},
    "OI": {"name": "菜籽油", "sector": "农产品"},
    "CF": {"name": "棉花", "sector": "农产品"},
    "LH": {"name": "生猪", "sector": "农产品"},
    "RB": {"name": "螺纹钢", "sector": "黑色"},
    "HC": {"name": "热卷", "sector": "黑色"},
    "I":  {"name": "铁矿石", "sector": "黑色"},
    "JM": {"name": "焦煤", "sector": "黑色"},
    "J":  {"name": "焦炭", "sector": "黑色"},
    "CU": {"name": "沪铜", "sector": "有色"},
    "AL": {"name": "沪铝", "sector": "有色"},
    "ZN": {"name": "沪锌", "sector": "有色"},
    "SN": {"name": "沪锡", "sector": "有色"},
    "NI": {"name": "沪镍", "sector": "有色"},
    "AO": {"name": "氧化铝", "sector": "有色"},
    "SC": {"name": "原油", "sector": "能化"},
    "SA": {"name": "纯碱", "sector": "能化"},
    "TA": {"name": "PTA", "sector": "能化"},
    "MA": {"name": "甲醇", "sector": "能化"},
    "FU": {"name": "燃料油", "sector": "能化"},
    "BU": {"name": "沥青", "sector": "能化"},
    "EG": {"name": "乙二醇", "sector": "能化"},
    "PP": {"name": "聚丙烯", "sector": "能化"},
    "L":  {"name": "聚乙烯", "sector": "能化"},
    "V":  {"name": "PVC", "sector": "能化"},
    "AU": {"name": "黄金", "sector": "贵金属"},
    "AG": {"name": "白银", "sector": "贵金属"},
    "BR": {"name": "沥青", "sector": "能化"},  # BR 沥青 vs BU 沥青 — BR实际是丁二烯橡胶
}

# 修正：BR 是丁二烯橡胶（Butadiene Rubber），不是沥青
SYMBOL_CONFIGS["BR"] = {"name": "丁二烯橡胶", "sector": "能化"}

# ── 字段插入顺序：symbol, extends, name, name_en, sector, ...其余 ──

def migrate_instrument(filepath: Path, dry_run: bool = True) -> list[str]:
    """迁移单个 instrument 文件，返回变更列表"""
    changes = []
    symbol = filepath.stem

    if symbol.startswith("_"):
        return []  # 跳过 _base.yaml, _templates.yaml

    config = SYMBOL_CONFIGS.get(symbol)
    if config is None:
        return [f"SKIP {symbol}: no SYMBOL_CONFIGS entry"]

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return [f"SKIP {symbol}: empty file"]

    # 补写 name
    if "name" not in data:
        data["name"] = config["name"]
        changes.append(f"  + name: {config['name']}")
    elif data["name"] != config["name"]:
        changes.append(f"  ~ name: {data['name']} → {config['name']}")
        data["name"] = config["name"]

    # 补写 name_en（symbol本身）
    if "name_en" not in data:
        data["name_en"] = symbol
        changes.append(f"  + name_en: {symbol}")

    # 补写 sector
    if "sector" not in data:
        data["sector"] = config["sector"]
        changes.append(f"  + sector: {config['sector']}")

    if not changes:
        return []

    # 重排字段顺序：symbol → extends → name → name_en → sector → 其余按原序
    ordered_keys = ["symbol", "extends", "name", "name_en", "sector"]
    new_data = {}
    for k in ordered_keys:
        if k in data:
            new_data[k] = data[k]
    for k in data:
        if k not in new_data:
            new_data[k] = data[k]

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(new_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return changes


def main() -> int:
    dry_run = "--exec" not in sys.argv

    if dry_run:
        print("=== DRY RUN (add --exec to apply changes) ===\n")
    else:
        print("=== EXECUTING MIGRATION ===\n")

    total_changes = 0
    for fp in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
        changes = migrate_instrument(fp, dry_run=dry_run)
        if changes:
            print(f"{fp.name}:")
            for c in changes:
                print(c)
            total_changes += len(changes)

    print(f"\nTotal changes: {total_changes}")
    if dry_run and total_changes > 0:
        print("Run with --exec to apply.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
