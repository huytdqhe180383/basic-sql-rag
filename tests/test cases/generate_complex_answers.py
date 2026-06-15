import json
import os

import psycopg2
from dotenv import load_dotenv

from db_config import get_postgres_connection_kwargs

TEST_CASES = [
    {
        "id": 1,
        "question": "How many order were refunded in 2017 and which city has the most canceled order?",
        "sql": """
        SELECT
          (SELECT COUNT(*) FROM orders WHERE order_status = 'returned' AND EXTRACT(YEAR FROM order_date) = 2017) AS refunded_2017_count,
          (SELECT g.city FROM orders o JOIN geography g ON o.zip = g.zip WHERE o.order_status = 'cancelled' GROUP BY g.city ORDER BY COUNT(*) DESC LIMIT 1) AS most_cancelled_city;
        """
    },
    {
        "id": 2,
        "question": "Give me our top 3 most profitable products (total revenue minus cogs) ever, but exclude anything that is currently flagged for overstock.",
        "sql": """
        WITH latest_inventory AS (
            SELECT product_id, overstock_flag
            FROM inventory
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory)
        )
        SELECT p.product_name, SUM(oi.quantity * (oi.unit_price - p.cogs) - oi.discount_amount) AS total_profit
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.product_id NOT IN (
            SELECT product_id FROM latest_inventory WHERE overstock_flag = TRUE
        )
        GROUP BY p.product_name
        ORDER BY total_profit DESC
        LIMIT 3;
        """
    },
    {
        "id": 3,
        "question": "Did we get more new folks from social media or organic search in the first half of 2020? And what was our total COGS for that period?",
        "sql": """
        SELECT
          (SELECT acquisition_channel FROM customers WHERE signup_date >= '2020-01-01' AND signup_date <= '2020-06-30' AND acquisition_channel IN ('social_media', 'organic_search') GROUP BY acquisition_channel ORDER BY COUNT(*) DESC LIMIT 1) AS top_channel,
          (SELECT SUM(COGS) FROM sales WHERE Date >= '2020-01-01' AND Date <= '2020-06-30') AS total_cogs_h1_2020;
        """
    },
    {
        "id": 4,
        "question": "I need the region that brought in the most revenue through apple pay in 2022. Also, what was the average days of supply for all products at the end of 2022?",
        "sql": """
        SELECT
          (SELECT g.region FROM orders o JOIN geography g ON o.zip = g.zip JOIN order_items oi ON o.order_id = oi.order_id WHERE o.payment_method = 'apple_pay' AND EXTRACT(YEAR FROM o.order_date) = 2022 GROUP BY g.region ORDER BY SUM(oi.quantity * oi.unit_price - oi.discount_amount) DESC LIMIT 1) AS top_apple_pay_region,
          (SELECT ROUND(AVG(days_of_supply), 2) FROM inventory WHERE snapshot_date = '2022-12-31') AS avg_days_of_supply_end_2022;
        """
    },
    {
        "id": 5,
        "question": "List the top 2 cities where guys buy the most stuff (total quantity) and their corresponding total revenue from guys.",
        "sql": """
        SELECT g.city, SUM(oi.quantity) AS total_quantity, SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS total_revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN geography g ON o.zip = g.zip
        WHERE c.gender = 'male'
        GROUP BY g.city
        ORDER BY total_quantity DESC
        LIMIT 2;
        """
    },
    {
        "id": 6,
        "question": "Show the number of times we ran out of stock for products in the 'streetwear' category, grouped by month for 2022. Also include the average fill rate for those items.",
        "sql": """
        SELECT i.month, SUM(CASE WHEN i.stockout_flag = TRUE THEN 1 ELSE 0 END) AS stockout_count, ROUND(AVG(i.fill_rate), 4) AS avg_fill_rate
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        WHERE i.year = 2022 AND p.category = 'streetwear'
        GROUP BY i.month
        ORDER BY i.month;
        """
    },
    {
        "id": 7,
        "question": "Which acquisition channel brings in the most folks who buy using Apple Pay, and what's the most common age bracket for those specific buyers?",
        "sql": """
        SELECT c.acquisition_channel, MODE() WITHIN GROUP (ORDER BY c.age_group) AS most_common_age_group
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.payment_method = 'apple_pay'
        GROUP BY c.acquisition_channel
        ORDER BY COUNT(DISTINCT c.customer_id) DESC
        LIMIT 1;
        """
    },
    {
        "id": 8,
        "question": "Find the district with the highest refund rate (returned orders / total orders). How much revenue did we lose to those returns?",
        "sql": """
        SELECT g.district,
               COUNT(CASE WHEN o.order_status = 'returned' THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) AS return_rate,
               SUM(CASE WHEN o.order_status = 'returned' THEN oi.quantity * oi.unit_price - oi.discount_amount ELSE 0 END) AS lost_revenue
        FROM orders o
        JOIN geography g ON o.zip = g.zip
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY g.district
        ORDER BY return_rate DESC
        LIMIT 1;
        """
    },
    {
        "id": 9,
        "question": "What's the average sell-through rate for our most heavily discounted product category in the last recorded inventory snapshot?",
        "sql": """
        WITH top_category AS (
            SELECT p.category
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY p.category
            ORDER BY AVG(oi.discount_amount) DESC
            LIMIT 1
        )
        SELECT t.category, ROUND(AVG(i.sell_through_rate), 4) AS avg_sell_through_rate
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        JOIN top_category t ON p.category = t.category
        WHERE i.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory)
        GROUP BY t.category;
        """
    },
    {
        "id": 10,
        "question": "We're looking at folks who signed up in 2018. Which source gave us the most loyal buyers (most orders per person), and what's their favorite color of stuff to buy?",
        "sql": """
        WITH loyal_channel AS (
            SELECT c.acquisition_channel
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE EXTRACT(YEAR FROM c.signup_date) = 2018
            GROUP BY c.acquisition_channel
            ORDER BY COUNT(o.order_id)::NUMERIC / NULLIF(COUNT(DISTINCT c.customer_id), 0) DESC
            LIMIT 1
        )
        SELECT l.acquisition_channel, MODE() WITHIN GROUP (ORDER BY p.color) AS favorite_color
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN loyal_channel l ON c.acquisition_channel = l.acquisition_channel
        WHERE EXTRACT(YEAR FROM c.signup_date) = 2018
        GROUP BY l.acquisition_channel;
        """
    }
]

def main():
    """Generate reference answers for the complex multi-intent test cases."""
    load_dotenv(override=True)
    conn = psycopg2.connect(**get_postgres_connection_kwargs(os.environ))
    conn.autocommit = True
    results = []

    for tc in TEST_CASES:
        cur = conn.cursor()
        try:
            cur.execute(tc["sql"])
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            clean_rows = []
            for row in rows:
                clean_row = []
                for v in row:
                    if isinstance(v, (int, float, str, bool)) or v is None:
                        clean_row.append(v)
                    else:
                        clean_row.append(str(v))
                clean_rows.append(clean_row)

            results.append({
                "id": tc["id"],
                "question": tc["question"],
                "reference_sql": tc["sql"].strip(),
                "answer": {
                    "columns": columns,
                    "rows": clean_rows,
                },
            })
            print(f"  [OK] Test {tc['id']:>2d}: ({len(rows)} rows)")
        except Exception as e:
            print(f"  [FAIL] Test {tc['id']:>2d}: {e}")
            results.append({
                "id": tc["id"],
                "question": tc["question"],
                "reference_sql": tc["sql"].strip(),
                "answer": None,
                "error": str(e),
            })
        finally:
            cur.close()

    conn.close()

    out_path = os.path.join(os.path.dirname(__file__), "complex_test_cases.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\\nWrote {len(results)} test cases to {out_path}")

if __name__ == "__main__":
    main()
