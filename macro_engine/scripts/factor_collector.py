import json
from pathlib import Path
from scripts.collectors.akshare_collector import collect_factor
import logging
from datetime import date, datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FactorCollector:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_batch(self, factors: list) -> dict:
        results = {
            'success': [],
            'failed': [],
            'data': {}
        }

        for factor in factors:
            factor_code = factor['factor_code']
            api_params = factor.get('api_params', {})

            try:
                data = collect_factor(factor_code, api_params)
                results['success'].append(factor_code)
                results['data'][factor_code] = data
                self._save_data(factor_code, data)
                logging.info(f"Successfully collected and saved data for {factor_code}")
            except Exception as e:
                results['failed'].append(factor_code)
                logging.error(f"Failed to collect data for {factor_code}: {e}")

        return results

    def _save_data(self, factor_code: str, data: dict):
        """保存数据为 JSON，自动处理日期类型"""
        def json_serializer(obj):
            """将 date/datetime 对象转为 ISO 格式字符串"""
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        file_path = self.output_dir / f"{factor_code}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=json_serializer)
        logging.info(f"Data saved to {file_path}")