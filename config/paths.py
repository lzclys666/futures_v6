from pathlib import Path

# 项目根目录（自动推导）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 各子目录
MACRO_ENGINE = PROJECT_ROOT / "macro_engine"
CRAWLERS = MACRO_ENGINE / "crawlers"
OUTPUT = MACRO_ENGINE / "output"
PIT_DB = MACRO_ENGINE / "pit_data.db"
CRAWLER_LOGS = CRAWLERS / "logs"
SHARED_EXCHANGE_DIR = MACRO_ENGINE / "data" / "crawlers" / "_shared" / "exchange"
CONFIG = PROJECT_ROOT / "config"
STRATEGIES = PROJECT_ROOT / "strategies"
SCRIPTS = PROJECT_ROOT / "scripts"
API_DIR = PROJECT_ROOT / "api"
SERVICES = PROJECT_ROOT / "services"
DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = PROJECT_ROOT / "data"

# 其他
BACKTEST = PROJECT_ROOT / "backtest.py"
