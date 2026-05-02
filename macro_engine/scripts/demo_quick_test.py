import sys
from pathlib import Path

# 调试信息（可保留或删除）
print("当前工作目录:", Path.cwd())
print("脚本所在目录:", Path(__file__).parent)
print("项目根目录应为:", Path(__file__).parent.parent)

# 关键修复：将根目录加入 sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"[修复] 已将 {project_root} 加入 sys.path")

import json
import sys
from pathlib import Path
from scripts.factor_collector import FactorCollector
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取因子需求文件
try:
    with open(Path("templates/factor_requirements_template.json"), "r", encoding="utf-8") as f:
        factor_requirements = json.load(f)
except FileNotFoundError:
    logging.error("[ERROR] Factor requirements file not found. Please check the path.")
    sys.exit(1)
except json.JSONDecodeError:
    logging.error("[ERROR] Failed to parse factor requirements file. Please check the JSON format.")
    sys.exit(1)

# 从 factor_requirements 中提取因子列表
try:
    factors = factor_requirements['factor_groups'][0]['factors']
except KeyError:
    logging.error("[ERROR] Invalid factor requirements file. Missing 'factor_groups' or 'factors' key.")
    sys.exit(1)

# 创建收集器（传入保存目录）
output_dir = "demo_output"
collector = FactorCollector(output_dir)

# 设置保存目录
output_dir_path = Path(output_dir)
output_dir_path.mkdir(exist_ok=True)

logging.info(f"输出目录: {output_dir_path.absolute()}")
logging.info(f"因子数量: {len(factors)}")

try:
    # 执行批量采集
    logging.info("开始批量采集...")
    results = collector.collect_batch(factors)

    logging.info(f"[OK] 批量采集完成")
    logging.info(f" 成功: {len(results['success'])}")
    logging.info(f" 失败: {len(results['failed'])}")

    # 显示结果详情
    if results['success']:
        logging.info("成功因子:")
        for factor_code in results['success']:
            data_info = results['data'].get(factor_code, {})
            logging.info(f"   - {factor_code}: {len(data_info)} records")

    if results['failed']:
        logging.warning("失败因子:")
        for factor_code in results['failed']:
            logging.warning(f"   - {factor_code}")

    # 根据失败数量返回退出码
    sys.exit(0 if len(results['failed']) == 0 else 1)

except Exception as e:
    logging.error(f"[ERROR] 批量采集失败: {e}")
    sys.exit(1)