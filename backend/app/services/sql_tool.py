import re
from dataclasses import dataclass, field

from google.genai import errors as genai_errors
from google.genai import types
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.config import get_settings
from app.prompts.sql_prompt import NO_QUERY_SENTINEL, SQL_SYSTEM_PROMPT
from app.services.llm import call_with_retry, get_client

settings = get_settings()

_FORBIDDEN_KEYWORDS = re.compile(
    r"(?i)\b("
    r"insert|update|delete|drop|alter|create|grant|revoke|truncate|"
    r"exec|execute|call|copy|merge|vacuum|analyze|explain|listen|notify|do|comment|"
    r"pg_sleep|dblink"
    r")\b"
)
_LIMIT_CLAUSE = re.compile(r"(?i)\blimit\s+\d+\b")
_CODE_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE)

_readonly_engine = create_engine(settings.sql_readonly_database_url, pool_pre_ping=True)


class SqlValidationError(Exception):
    """Raised when generated SQL fails the safety guardrail."""


class SqlExecutionError(Exception):
    """Raised when a validated query fails to execute against the database."""


class SqlGenerationError(Exception):
    """Raised when the NL-to-SQL generation call fails (e.g. a transient LLM API error)."""


@dataclass
class SqlToolResult:
    applicable: bool
    generated_sql: str | None
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def _strip_code_fences(sql: str) -> str:
    return _CODE_FENCE.sub("", sql.strip()).strip()


def generate_sql(question: str) -> str:
    """Turns a natural-language question into raw SQL text (or the NO_QUERY sentinel).

    Retries once on a transient server-side error (e.g. "model overloaded"); anything else,
    or a persistent failure, is raised as SqlGenerationError for the caller to handle.
    """
    try:
        response = call_with_retry(
            get_client().models.generate_content,
            model=settings.chat_model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SQL_SYSTEM_PROMPT,
                temperature=0,
            ),
        )
    except genai_errors.APIError as exc:
        raise SqlGenerationError(str(exc)) from exc
    return _strip_code_fences(response.text or "")


def validate_sql(sql: str) -> str:
    """Enforces: single statement, SELECT-only, no dangerous keywords/comments.

    Returns the validated SQL with a LIMIT clause appended if one is missing.
    Raises SqlValidationError on any violation.
    """
    candidate = sql.strip()
    if not candidate:
        raise SqlValidationError("Generated SQL was empty")

    if candidate.endswith(";"):
        candidate = candidate[:-1].strip()
    if ";" in candidate:
        raise SqlValidationError("Multiple SQL statements are not allowed")

    if not re.match(r"(?is)^select\b", candidate):
        raise SqlValidationError("Only SELECT statements are allowed")

    if _FORBIDDEN_KEYWORDS.search(candidate):
        raise SqlValidationError("Disallowed SQL keyword detected")

    if "--" in candidate or "/*" in candidate:
        raise SqlValidationError("SQL comments are not allowed")

    if not _LIMIT_CLAUSE.search(candidate):
        candidate = f"{candidate} LIMIT {settings.sql_max_rows}"

    return candidate


def _run_readonly(sql: str) -> tuple[list[str], list[dict]]:
    try:
        with _readonly_engine.connect() as conn, conn.begin():
            conn.execute(text(f"SET LOCAL statement_timeout = {settings.sql_statement_timeout_ms}"))
            conn.execute(text("SET TRANSACTION READ ONLY"))
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        return columns, rows
    except DBAPIError as exc:
        raise SqlExecutionError(str(exc.orig)) from exc


def execute_sql(question: str) -> SqlToolResult:
    """Tool entrypoint: natural-language question -> generated SQL -> validated -> executed.

    Returns a result with applicable=False (no generated_sql) if the question can't be
    answered from the orders schema, so the caller can fall back gracefully.
    """
    raw_sql = generate_sql(question)
    if raw_sql.strip().upper() == NO_QUERY_SENTINEL:
        return SqlToolResult(applicable=False, generated_sql=None)

    validated_sql = validate_sql(raw_sql)
    columns, rows = _run_readonly(validated_sql)
    return SqlToolResult(applicable=True, generated_sql=validated_sql, columns=columns, rows=rows)
