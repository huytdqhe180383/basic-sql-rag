from beacon.schema_graph import build_schema_graph, relation_paths


SEMANTIC_MODEL = [
    {
        "source_table": "customers",
        "columns": [{"name": "customer_id"}, {"name": "zip"}],
        "relations": [{"from": "customers.customer_id", "to": "orders.customer_id"}],
    },
    {
        "source_table": "orders",
        "columns": [{"name": "order_id"}, {"name": "customer_id"}],
        "relations": [{"from": "orders.order_id", "to": "order_items.order_id"}],
    },
    {
        "source_table": "order_items",
        "columns": [{"name": "order_id"}, {"name": "product_id"}],
        "relations": [{"from": "order_items.product_id", "to": "products.product_id"}],
    },
    {"source_table": "products", "columns": [{"name": "product_id"}], "relations": []},
]


def test_relation_paths_connect_selected_tables_with_bridge_tables():
    graph = build_schema_graph(SEMANTIC_MODEL)
    paths = relation_paths(graph, {"customers", "products"}, max_hops=3)

    assert "customers.customer_id -> orders.customer_id" in paths
    assert "orders.order_id -> order_items.order_id" in paths
    assert "order_items.product_id -> products.product_id" in paths
