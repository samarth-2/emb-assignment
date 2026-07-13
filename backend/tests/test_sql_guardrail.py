import pytest

from app.services.sql_tool import SqlValidationError, validate_sql


def test_valid_select_passes_unchanged_when_limit_present():
    sql = "SELECT * FROM orders WHERE status = 'pending' LIMIT 10"
    assert validate_sql(sql) == sql


def test_limit_appended_when_missing():
    sql = "SELECT count(*) FROM orders WHERE status = 'pending'"
    result = validate_sql(sql)
    assert result.endswith("LIMIT 200")
    assert result.startswith(sql)


def test_lowercase_select_is_accepted():
    sql = "select * from orders limit 5"
    assert validate_sql(sql) == sql


def test_trailing_semicolon_is_stripped():
    sql = "SELECT * FROM orders LIMIT 5;"
    assert validate_sql(sql) == "SELECT * FROM orders LIMIT 5"


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO orders (order_id) VALUES ('x')",
        "UPDATE orders SET status = 'delivered'",
        "DELETE FROM orders",
        "DROP TABLE orders",
        "ALTER TABLE orders ADD COLUMN foo text",
        "GRANT SELECT ON users TO public",
        "TRUNCATE orders",
        "CREATE TABLE evil (id int)",
    ],
)
def test_destructive_statements_are_rejected(sql):
    with pytest.raises(SqlValidationError):
        validate_sql(sql)


def test_non_select_statement_is_rejected():
    with pytest.raises(SqlValidationError):
        validate_sql("SHOW server_version")


def test_multiple_statements_are_rejected():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM orders; DROP TABLE orders;")


def test_sql_comments_are_rejected():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM orders -- ignore rest\nWHERE 1=1")
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM orders /* comment */ WHERE 1=1")


def test_empty_sql_is_rejected():
    with pytest.raises(SqlValidationError):
        validate_sql("   ")
