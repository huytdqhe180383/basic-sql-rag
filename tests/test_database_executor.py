import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_executor import DatabaseExecutor, SqlValidationError


def test_validate_sql_rejects_multiple_statements():
    executor = DatabaseExecutor(
        connection_kwargs={},
        allowed_tables={"orders"},
    )

    with pytest.raises(SqlValidationError):
        executor.validate_sql("SELECT * FROM orders; DELETE FROM orders")


def test_validate_sql_rejects_writes():
    executor = DatabaseExecutor(
        connection_kwargs={},
        allowed_tables={"orders"},
    )

    with pytest.raises(SqlValidationError):
        executor.validate_sql("DELETE FROM orders")


def test_validate_sql_allows_cte_and_real_tables_only():
    executor = DatabaseExecutor(
        connection_kwargs={},
        allowed_tables={"orders", "order_items"},
    )

    result = executor.validate_sql(
        """
        WITH ranked_orders AS (
            SELECT order_id FROM orders
        )
        SELECT oi.order_id
        FROM ranked_orders ro
        JOIN order_items oi ON ro.order_id = oi.order_id
        """
    )

    assert result.normalized_sql.startswith("WITH ranked_orders")
    assert result.referenced_tables == {"orders", "order_items"}


def test_count_wrapper_preserves_single_statement_sql():
    executor = DatabaseExecutor(
        connection_kwargs={},
        allowed_tables={"orders"},
    )

    wrapped_sql = executor.build_count_query("SELECT order_id FROM orders ORDER BY order_id")

    assert wrapped_sql == (
        "SELECT COUNT(*) FROM "
        "(SELECT order_id FROM orders ORDER BY order_id) AS beacon_count"
    )
