import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
LOGS_DIR = BASE_DIR / "logs"

# Default to local SQLite database; override with PostgreSQL URL via DATABASE_URL env var
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'data_pipeline.db'}",
)

for directory in [DATA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
