"""Shared helpers for loading PostgreSQL connection settings.

These helpers keep credential handling in one place so local scripts do not
need to hardcode secrets before connecting to the database.
"""

from collections.abc import Mapping


def get_postgres_connection_kwargs(env: Mapping[str, str]) -> dict[str, str]:
    """Build a psycopg2 connection kwargs dict from environment variables."""
    return {
        "host": env.get("PGHOST", "localhost"),
        "port": env.get("PGPORT", "5432"),
        "user": env.get("PGUSER", "postgres"),
        "password": env.get("PGPASSWORD", ""),
        "dbname": env.get("PGDATABASE", "postgres"),
    }
