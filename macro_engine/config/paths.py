"""
Path constants - macro_engine.config.paths
"""
from pathlib import Path

MACRO_ENGINE = Path(__file__).resolve().parent.parent
DOCS_DIR = MACRO_ENGINE / "docs"
OUTPUT = MACRO_ENGINE / "output"
PIT_DB = MACRO_ENGINE / "pit_data.db"
CRAWLERS = MACRO_ENGINE / "crawlers"
CRAWLER_LOGS = CRAWLERS / "logs"
