# scripts/daily_scoring.py
"""
每日打分流水线 - 输出 per-symbol CSV 文件（Option A 统一格式）
==============================================================================
输出路径：D:\futures_v6\macro_engine\output\{SYMBOL}_macro_daily_{YYYYMMDD}.csv
格式：SUMMARY 行 + FACTOR 行（与 workspace API 读取格式完全一致）

用途：
  - D:\futures_v6\api\macro_scoring_engine.py 读取此目录
  - VeighNa 策略可通过 macro_demo_strategy.py 读取
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import csv
import logging
import logging.handlers
import yaml
import os
from datetime import date, datetime, timedelta
from core.data.pit_service import PitDataService
from core.pipeline.nodes import NormalizeNode, OrthogonalizeNode, WeightNode, DirectionNode
from core.pipeline.base import Pipeline
from core.normalizer.robust_normalizer import MADNormalizer
from event_bus import get_event_bus

# ============ 路径配置（Option A 统一到 D:\futures_v6\macro_engine\output） ============
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

ENGINE_VERSION = "d_engine_v1.0"

# ============ 魔法数字常量 ============
# 方向阈值
DIRECTION_LONG_SCORE = 40      # 触发 LONG 信号的最低标准分
DIRECTION_SHORT_SCORE = 60     # 触发 SHORT 信号的最高标准分
DIRECTION_CONFIRM_DAYS = 2     # 方向确认所需连续天数

# 有效因子质量阈值
VALID_FACTOR_RATIO_THRESHOLD = 0.5   # 有效因子比例最低要求（低于此值输出质量告警）

# 默认综合评分（用于无数据时的 fallback）
DEFAULT_FINAL_SCORE = 50.0

# composite_score 映射：pipeline 输出 0~100 → -1~+1
_SCORE_RANGE_HALF = 50.0  # (final_score - 50) / 50.0 映射的除数

# 日志滚动配置
LOG_ROTATION_WHEN = 'midnight'
LOG_ROTATION_BACKUP_COUNT = 7

# ============ 日志配置 ============
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "daily_scoring.log"

_logger = logging.getLogger("daily_scoring")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE, when='midnight', backupCount=7, encoding='utf-8'
    )
    _handler.setFormatter(logging.Formatter(
        '%(asctime)s,%(msecs)03d [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    _logger.addHandler(_handler)


def _snake_to_camel(snake_str: str) -> str:
    """snake_case → camelCase 转换"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def _to_camel_case(row: dict) -> dict:
    """将 dict 的 snake_case 键转换为 camelCase"""
    return {_snake_to_camel(k): v for k, v in row.items()}


def _is_valid_ic_value(val) -> bool:
    """判断 icValue 是否为有效值（非零、非None、非空字符串）"""
    if val is None:
        return False
    if isinstance(val, str):
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
    try:
        return float(val) != 0.0
    except (ValueError, TypeError):
        return False


def load_factor_metdata(symbol: str) -> dict:
    """
    从 config/factors/{SYMBOL}/ 目录加载因子元数据
    Returns: {factor_code: {"name": ..., "direction": ..., "base_weight": ...}}
    """
    factor_dir = Path(__file__).parent.parent / "config" / "factors" / symbol.upper()
    meta = {}
    if not factor_dir.exists():
        return meta
    for yaml_file in factor_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            if cfg and cfg.get('is_active', True):
                fc = cfg.get('factor_code', yaml_file.stem)
                meta[fc] = {
                    'name': cfg.get('factor_name', fc),
                    'direction': cfg.get('direction', 1),
                    'base_weight': cfg.get('base_weight', 0.05),
                }
        except Exception:
            pass
    return meta


def load_symbols_from_config():
    """从 config/settings.yaml 读取品种列表"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    default_symbols = ["RU"]

    if not config_path.exists():
        print(f"警告：配置文件 {config_path} 不存在，使用默认品种列表")
        return default_symbols

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        symbols = config.get("symbols", [])
        if not symbols:
            print("警告：配置文件中 symbols 为空，使用默认品种列表")
            return default_symbols
        return symbols
    except Exception as e:
        print(f"警告：读取配置文件失败 ({e})，使用默认品种列表")
        return default_symbols


def run_daily_scoring():
    """每日运行，生成 per-symbol CSV 文件（含因子明细）"""
    event_bus = get_event_bus()

    # 初始化数据服务
    data_provider = PitDataService()

    # 从配置文件加载品种列表
    symbols = load_symbols_from_config()
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    today_yyyymmdd = today.strftime('%Y%m%d')
    updated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')

    print(f"\n{'='*60}")
    print(f"  D引擎每日打分流水线 - {today_str}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    for symbol in symbols:
        symbol = symbol.upper()
        print(f"\n--- {symbol} ---")

        # 获取因子元数据
        factor_meta = load_factor_metdata(symbol)

        # 构建流水线
        nodes = [
            NormalizeNode(data_provider=data_provider),
            OrthogonalizeNode(),
            WeightNode(),
            DirectionNode(thresholds=(DIRECTION_LONG_SCORE, DIRECTION_SHORT_SCORE), confirm_days=DIRECTION_CONFIRM_DAYS)
        ]
        pipeline = Pipeline(nodes)

        # 获取当日快照
        snapshot = data_provider.get_snapshot(symbol, today)
        raw_factors = {code: val[0] for code, val in snapshot.items()}

        if not raw_factors:
            print(f"  警告：{symbol} 无可用因子数据，跳过")
            continue

        initial_data = {'raw_factors': raw_factors}
        context = {'symbol': symbol, 'as_of_date': today}

        # 用于收集输出行的容器
        output_rows = []

        def output_formatter(data: dict, ctx: dict):
            """流水线结束后回调：构建 CSV 行（snake_case → camelCase）"""
            normalized = data.get('normalized_factors', {})
            weights = data.get('weights', {})
            final_score = data.get('final_score', DEFAULT_FINAL_SCORE)
            direction = data.get('direction', 'NEUTRAL')
            factor_count = len(normalized)

            # 计算 composite_score（pipeline 0~100 → -1~+1）
            composite_score = (final_score - _SCORE_RANGE_HALF) / _SCORE_RANGE_HALF

            # SUMMARY 行（内部使用 snake_case，输出时转 camelCase）
            summary_row_snake = {
                'symbol': symbol,
                'date': today_str,
                'row_type': 'SUMMARY',
                'composite_score': round(composite_score, 4),
                'direction': direction,
                'factor_count': factor_count,
                'updated_at': updated_at,
                'engine_version': ENGINE_VERSION,
                'factor_code': '',
                'factor_name': '',
                'raw_value': '',
                'normalized_score': '',
                'weight': '',
                'contribution': '',
                'contribution_polarity': '',
                'ic_value': ''
            }
            output_rows.append(_to_camel_case(summary_row_snake))

            # FACTOR 行
            for fc, norm_score in normalized.items():
                wt = weights.get(fc, 0.0)
                contribution = norm_score * wt
                meta = factor_meta.get(fc, {})
                fd_map = {'1': 'positive', '-1': 'negative'}
                fd_raw = str(meta.get('direction', '1')).strip()
                fd = fd_map.get(fd_raw, 'positive')
                raw_val = raw_factors.get(fc, '')

                factor_row_snake = {
                    'symbol': symbol,
                    'date': today_str,
                    'row_type': 'FACTOR',
                    'composite_score': round(composite_score, 4),
                    'direction': direction,
                    'factor_count': factor_count,
                    'updated_at': updated_at,
                    'engine_version': ENGINE_VERSION,
                    'factor_code': fc,
                    'factor_name': meta.get('name', fc),
                    'raw_value': raw_val,
                    'normalized_score': round(norm_score, 4),
                    'weight': round(wt, 4),
                    'contribution': round(contribution, 4),
                    'contribution_polarity': fd,
                    'ic_value': 0.0
                }
                output_rows.append(_to_camel_case(factor_row_snake))

        pipeline.set_output_formatter(output_formatter)
        result = pipeline.run(initial_data, context)

        if not output_rows:
            print(f"  跳过（无输出）")
            continue

        # ------------------- 质量检查 -------------------
        factor_rows = [r for r in output_rows if r.get('rowType') == 'FACTOR']
        valid_factor_count = sum(
            1 for r in factor_rows if _is_valid_ic_value(r.get('icValue'))
        )
        total_factor_count = len(factor_rows)
        valid_ratio = valid_factor_count / total_factor_count if total_factor_count > 0 else 0.0

        if valid_ratio < VALID_FACTOR_RATIO_THRESHOLD:
            warn_msg = (
                f"[质量告警] {symbol} 有效因子比例过低: "
                f"有效={valid_factor_count}/{total_factor_count} "
                f"({valid_ratio:.1%}), 阈值={int(VALID_FACTOR_RATIO_THRESHOLD * 100)}%"
            )
            _logger.warning(warn_msg)
            print(f"  ⚠️ {warn_msg}")
        else:
            _logger.info(
                f"{symbol} 有效因子: {valid_factor_count}/{total_factor_count} "
                f"({valid_ratio:.1%})"
            )

        # ------------------- 写 CSV -------------------
        csv_path = OUTPUT_DIR / f"{symbol}_macro_daily_{today_yyyymmdd}.csv"
        fieldnames = list(output_rows[0].keys())

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        direction = result.get('direction', 'NEUTRAL')
        score = result.get('final_score', DEFAULT_FINAL_SCORE)
        composite = (score - _SCORE_RANGE_HALF) / _SCORE_RANGE_HALF
        normalized_count = len(result.get('normalized_factors', {}))
        print(f"  得分={score:.2f} ({direction}), composite={composite:+.4f}")
        print(f"  因子数={normalized_count}, 文件已写入: {csv_path.name}")

    # 发布事件总线通知
    event_bus = get_event_bus()
    scoring_payload = {
        "script": "daily_scoring.py",
        "interface": "I005",
        "date": today_str,
        "symbols_count": len(symbols),
        "output_dir": str(OUTPUT_DIR),
        "engine_version": ENGINE_VERSION,
    }
    event_bus.publish("SCORING_COMPLETE", scoring_payload)

    print(f"\n{'='*60}")
    print(f"  全部完成，输出目录: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_daily_scoring()
