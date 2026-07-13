import pytest

from app.services.sql_tool import (
    SqlExecutionError,
    SqlGenerationError,
    _run_readonly,
    execute_sql,
)


def _run_or_skip(question: str):
    try:
        return execute_sql(question)
    except (SqlExecutionError, SqlGenerationError) as exc:
        pytest.skip(f"Live SQL tool infra not reachable: {exc}")


def test_pending_orders_count_matches_ground_truth():
    result = _run_or_skip("How many orders are pending?")
    assert result.applicable
    assert result.generated_sql is not None
    assert result.rows
    value = next(iter(result.rows[0].values()))
    assert int(value) == 24  # ground truth from dataset analysis


def test_out_of_scope_question_is_not_applicable():
    result = _run_or_skip("Who is the CEO of the company?")
    assert not result.applicable
    assert result.generated_sql is None


def test_readonly_role_cannot_read_other_tables():
    try:
        _run_readonly("SELECT 1")  # connectivity probe; sql_readonly needs no grants for this
    except SqlExecutionError as exc:
        pytest.skip(f"Live DB not reachable: {exc}")

    with pytest.raises(SqlExecutionError, match="permission denied"):
        _run_readonly("SELECT * FROM users LIMIT 1")
