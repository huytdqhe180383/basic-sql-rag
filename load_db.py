import os

import psycopg2
from dotenv import load_dotenv

from db_config import get_postgres_connection_kwargs


def load():
    """Create the schema and bulk-load local CSV files into PostgreSQL."""
    load_dotenv(override=True)
    conn = psycopg2.connect(**get_postgres_connection_kwargs(os.environ))
    conn.autocommit = True
    cur = conn.cursor()

    # 1. run schema
    with open('sql/00_simple_schema.sql', 'r') as f:
        cur.execute(f.read())

    print("Schema created.")

    # 2. load data
    tables = [
        'geography', 'products', 'customers', 'orders',
        'order_items', 'sales', 'inventory'
    ]
    for table in tables:
        csv_file = f'data/processed/{table}.csv'
        if os.path.exists(csv_file):
            with open(csv_file, 'r', encoding='utf-8') as f:
                next(f)  # Skip the CSV header row before COPY FROM STDIN.
                cur.copy_expert(f"COPY {table} FROM STDIN WITH CSV", f)
            print(f"Loaded {table}")
        else:
            print(f"Missing {csv_file}")

    conn.close()


if __name__ == '__main__':
    load()
