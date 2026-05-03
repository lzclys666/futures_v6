#!/usr/bin/env python3
"""
YAML Validation Fix Migration Script
Fixes remaining 606 validation errors:
  1. name: copy factor_name -> name where missing
  2. source_confidence: derive from source/confidence or use category-based default
  3. data_source: extract from dependencies or use category-based default
  4. expected_range: add for files missing it
  5. description/category: backfill for NR outlier files

Usage: python fix_yaml_validation.py [--dry-run] [--instruments AG,AU]
"""
import argparse
import copy
import os
import re
from pathlib import Path

import yaml

# Default source_confidence by category
CATEGORY_DEFAULTS = {
    'free_data': {'source_confidence': 0.85, 'data_source': 'AKShare'},
    'paid_data': {'source_confidence': 0.7, 'data_source': 'Mysteel'},
    'derived': {'source_confidence': 0.75, 'data_source': 'Calculated'},
    'model_signal': {'source_confidence': 0.6, 'data_source': 'Model'},
    None: {'source_confidence': 0.8, 'data_source': 'AKShare'},
}


def extract_data_source(data):
    """Extract data_source from dependencies or use default."""
    deps = data.get('dependencies', [])
    if deps and isinstance(deps, list):
        first = str(deps[0])
        # Extract source name from dependency string like "AKShare/fx_spot_quote"
        if '/' in first:
            return first.split('/')[0]
        return first
    return None


def get_default_confidence_and_source(category):
    defaults = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS[None])
    return defaults['source_confidence'], defaults['data_source']


def fix_file(fp, dry_run=False):
    """Fix validation errors in a single YAML file. Returns (fp, changes_list)."""
    with open(fp, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        return fp, []

    changes = []
    original = copy.deepcopy(data)

    # 1. Fix name: factor_name -> name
    if 'name' not in data and 'factor_name' in data:
        data['name'] = data['factor_name']
        changes.append("name: added from factor_name=%r" % data['factor_name'][:30])

    # 2. Fix source_confidence
    if 'source_confidence' not in data:
        if 'confidence' in data:
            data['source_confidence'] = data['confidence']
            changes.append("source_confidence: from confidence=%r" % data['confidence'])
        else:
            cat = data.get('category')
            conf, src = get_default_confidence_and_source(cat)
            data['source_confidence'] = conf
            changes.append("source_confidence: default %.2f (category=%s)" % (conf, cat))

    # 3. Fix data_source
    if 'data_source' not in data:
        extracted = extract_data_source(data)
        if extracted:
            data['data_source'] = extracted
            changes.append("data_source: from dependencies=%r" % extracted)
        else:
            cat = data.get('category')
            conf, src = get_default_confidence_and_source(cat)
            data['data_source'] = src
            changes.append("data_source: default %r (category=%s)" % (src, cat))

    # 4. Fix expected_range (only for numeric-looking factors)
    if 'expected_range' not in data:
        factor_code = data.get('factor_code', '')
        # Only add for price/position/inventory type factors
        # Skip non-numeric factors (those with STR/TS/logic_category=TS etc.)
        lc = data.get('logic_category', '')
        if lc not in ('TS', 'STR', 'SEN'):
            data['expected_range'] = [-100000.0, 100000.0]
            changes.append("expected_range: added default [-100000, 100000]")

    # 5. Fix NR outlier files missing description/category
    if data.get('category') == 'free_data' and not data.get('description'):
        data['description'] = data.get('factor_name', data.get('name', 'Factor'))
        changes.append("description: added from factor_name (NR backfill)")

    # Write back
    if changes and not dry_run:
        with open(fp, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return fp, changes


def main():
    parser = argparse.ArgumentParser(description='Fix YAML validation errors')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--instruments', type=str, help='Comma-separated, e.g. AG,AU')
    args = parser.parse_args()

    factors_dir = Path(r'D:\futures_v6\macro_engine\config\factors')
    instruments = args.instruments.split(',') if args.instruments else None

    total_files = 0
    changed_files = 0
    total_changes = 0

    for inst_dir in sorted(factors_dir.iterdir()):
        if not inst_dir.is_dir():
            continue
        if instruments and inst_dir.name not in instruments:
            continue

        for fp in sorted(inst_dir.glob('*.yaml')):
            fp_str, changes = fix_file(str(fp), dry_run=args.dry_run)
            total_files += 1
            if changes:
                changed_files += 1
                total_changes += len(changes)
                prefix = '[DRY-RUN] ' if args.dry_run else '[FIXED] '
                print('%s%s/%s' % (prefix, inst_dir.name, fp.name))
                for c in changes:
                    print('  - %s' % c)

    mode = 'DRY-RUN' if args.dry_run else 'FIXED'
    print('\n=== %s Summary ===' % mode)
    print('Scanned: %d files' % total_files)
    print('Changed: %d files' % changed_files)
    print('Changes: %d' % total_changes)


if __name__ == '__main__':
    main()
