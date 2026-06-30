"""Load processed CSV files into PostgreSQL."""

from __future__ import annotations

import psycopg2
from dotenv import load_dotenv

from beacon.config import PROCESSED_DATA_DIR, SQL_DIR, get_db_kwargs


TABLES = [
    "geography",
    "products",
    "customers",
    "orders",
    "order_items",
    "sales",
    "inventory",
]


def load() -> None:
    """Create schema and bulk-load processed CSVs into PostgreSQL."""
    load_dotenv(override=True)
    conn = psycopg2.connect(**get_db_kwargs())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute((SQL_DIR / "00_simple_schema.sql").read_text(encoding="utf-8"))
            print("Schema created.")
            for table in TABLES:
                csv_path = PROCESSED_DATA_DIR / f"{table}.csv"
                if not csv_path.exists():
                    print(f"Missing {csv_path}")
                    continue
                with csv_path.open(encoding="utf-8") as handle:
                    next(handle)
                    cur.copy_expert(f"COPY {table} FROM STDIN WITH CSV", handle)
                print(f"Loaded {table}")
    finally:
        conn.close()


def main() -> None:
    """CLI entry point."""
    load()


if __name__ == "__main__":
    main()
