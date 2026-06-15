import db_config


def test_get_postgres_connection_kwargs_uses_defaults():
    env = {}

    result = db_config.get_postgres_connection_kwargs(env)

    assert result == {
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "",
        "dbname": "postgres",
    }


def test_get_postgres_connection_kwargs_uses_env_values():
    env = {
        "PGHOST": "db.example.internal",
        "PGPORT": "15432",
        "PGUSER": "analytics",
        "PGPASSWORD": "secret-from-env",
        "PGDATABASE": "warehouse",
    }

    result = db_config.get_postgres_connection_kwargs(env)

    assert result == {
        "host": "db.example.internal",
        "port": "15432",
        "user": "analytics",
        "password": "secret-from-env",
        "dbname": "warehouse",
    }
