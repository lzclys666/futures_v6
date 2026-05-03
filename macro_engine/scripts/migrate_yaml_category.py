#!/usr/bin/env python3
"""
YAML Category migration script.
Maps logic_category to standard category enum, fixes expected_range format.
Usage: python migrate_yaml_category.py [--dry-run] [--instruments AG,AU,CU]
"""
import argparse
import copy
import os
import re
import sys
from pathlib import Path

import yaml

# === Mapping table ===
LOGIC_TO_CATEGORY = {
    'STK': 'free_data',
    'STR': 'free_data',
    'QTY': 'paid_data',
    'SPD': 'derived',
    'POS': 'free_data',
    'FX': 'free_data',
    'SEN': 'derived',
    'DEM': 'paid_data',
    'CST': 'free_data',
    'INV': 'free_data',
    'TS': 'free_data',
    'PRI': 'free_data',
    'FRT': 'free_data',
    'SUP': 'free_data',
    'VAL': 'derived',
    'INF': 'free_data',
    'RAT': 'free_data',
    'CTR': 'free_data',
    'ARB': 'derived',
    'WTH': 'free_data',
    'MGN': 'derived',
    'BASIS': 'derived',
    'CROSS': 'derived',
    'PRC': 'free_data',
}

# Old category values -> new category values
OLD_CATEGORY_MAP = {
    'inventory': 'free_data',
    'spread': 'derived',
    'price': 'free_data',
    'position': 'free_data',
    'supply': 'free_data',
    'operation': 'derived',
    'cost': 'free_data',
    'macro': 'free_data',
    'basis': 'derived',
    'fx': 'free_data',
    'event': 'free_data',
    'warehouse_receipt': 'free_data',
    'demand': 'paid_data',
}

VALID_CATEGORIES = {'free_data', 'paid_data', 'derived', 'model_signal'}


def fix_expected_range(er):
    if isinstance(er, list) and len(er) == 1 and isinstance(er[0], str):
        s = er[0].strip()
        m = re.match(r'^(-?[\d.]+)\s*-\s*(-?[\d.]+)$', s)
        if m:
            return [float(m.group(1)), float(m.group(2))]
    if isinstance(er, list) and len(er) == 2 and all(isinstance(x, (int, float)) for x in er):
        return er
    return er


def migrate_file(fp, dry_run=False):
    with open(fp, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        return fp, []

    changes = []
    cat = data.get('category')
    lc = data.get('logic_category')

    # 1. Fix category field
    if cat and cat not in VALID_CATEGORIES:
        new_cat = OLD_CATEGORY_MAP.get(cat)
        if new_cat:
            data['category'] = new_cat
            changes.append('category: %r -> %r' % (cat, new_cat))
        elif lc and lc in LOGIC_TO_CATEGORY:
            new_cat = LOGIC_TO_CATEGORY[lc]
            data['category'] = new_cat
            changes.append('category: %r -> %r (via logic_category=%s)' % (cat, new_cat, lc))

    if not data.get('category') and lc and lc in LOGIC_TO_CATEGORY:
        new_cat = LOGIC_TO_CATEGORY[lc]
        data['category'] = new_cat
        changes.append('category: added %r (from logic_category=%s)' % (new_cat, lc))

    # 2. Fix expected_range
    er = data.get('expected_range')
    if er:
        fixed_er = fix_expected_range(er)
        if fixed_er != er:
            data['expected_range'] = fixed_er
            changes.append('expected_range: %r -> %r' % (er, fixed_er))

    # 3. Write back
    if changes and not dry_run:
        with open(fp, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return fp, changes


def main():
    parser = argparse.ArgumentParser(description='Migrate YAML category fields')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    parser.add_argument('--instruments', type=str, help='Comma-separated instrument list, e.g. AG,AU,CU')
    args = parser.parse_args()

    factors_dir = Path(r'D:\futures_v6\macro_engine\config\factors')
    instruments = args.instruments.split(',') if args.instruments else None

    total_changes = 0
    total_files = 0
    changed_files = 0

    for inst_dir in sorted(factors_dir.iterdir()):
        if not inst_dir.is_dir():
            continue
        if instruments and inst_dir.name not in instruments:
            continue

        for fp in sorted(inst_dir.glob('*.yaml')):
            fp_str, changes = migrate_file(str(fp), dry_run=args.dry_run)
            total_files += 1
            if changes:
                changed_files += 1
                total_changes += len(changes)
                prefix = '[DRY-RUN] ' if args.dry_run else '[MIGRATED] '
                print('%s%s/%s' % (prefix, inst_dir.name, fp.name))
                for c in changes:
                    print('  - %s' % c)

    mode = 'DRY-RUN' if args.dry_run else 'MIGRATED'
    print('\n=== %s Summary ===' % mode)
    print('Scanned: %d files' % total_files)
    print('Changed: %d files' % changed_files)
    print('Changes: %d' % total_changes)


if __name__ == '__main__':
    main()
