"""Small configuration and path helpers for Beacon."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
SEMANTIC_MODEL_DIR = DATA_DIR / "semantic_model"
FEW_SHOT_QUERIES_PATH = DATA_DIR / "few_shot_queries.json"
INDEX_DIR = DATA_DIR / "indices"
SCHEMA_INDEX_DIR = INDEX_DIR / "schema"
FEW_SHOT_INDEX_DIR = INDEX_DIR / "few_shot"


def get_db_kwargs(env: dict | None = None) -> dict[str, str]:
    """Return psycopg2 connection kwargs from environment-like values."""
    env = env or os.environ
    return {
        "host": env.get("PGHOST", "localhost"),
        "port": env.get("PGPORT", "5432"),
        "user": env.get("PGUSER", "postgres"),
        "password": env.get("PGPASSWORD", ""),
        "dbname": env.get("PGDATABASE", "postgres"),
    }


def load_settings() -> dict:
    """Load OpenAI and database settings used by the pipeline."""
    load_dotenv(override=True)
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_api_base": os.getenv("OPENAI_API_BASE"),
        "model": os.getenv("SQL_AGENT_LLM_STRONG_MODEL"),
        "db": get_db_kwargs(),
    }
