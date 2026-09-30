"""Filesystem locations shared across the Python packages."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROL_DIR = PROJECT_ROOT / "control"
DATALAKE_DIR = PROJECT_ROOT / "datalake"
DATAMARTS_DIR = PROJECT_ROOT / "datamarts"
METADATA_DB_PATH = DATAMARTS_DIR / "metadata.db"
JSON_INDEX_PATH = DATAMARTS_DIR / "inverted_index.json"
FOLDER_INDEX_DIR = DATAMARTS_DIR / "inverted_index"
