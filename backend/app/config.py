from functools import lru_cache
from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    database_url_sync_migrations: str | None = None

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # LLM
    google_api_key: str = ""
    chat_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    # RAG retrieval
    retrieval_top_k: int = 4
    retrieval_distance_threshold: float = 0.4

    # Text-to-SQL guardrails
    sql_readonly_password: str = "sql_readonly_dev_password"
    sql_statement_timeout_ms: int = 5000
    sql_max_rows: int = 200

    # App
    cors_origins: str = "http://localhost:3000"
    pinned_current_date: str = "2026-06-15"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sql_readonly_database_url(self) -> str:
        """Same host/port/db as DATABASE_URL, but connects as the least-privilege
        `sql_readonly` role (SELECT-only on `orders`; created in migration 0002).

        Supabase's connection pooler (Supavisor) is multi-tenant and routes by a
        project-ref suffix embedded in the username (`user.project_ref`) rather than
        by database name. If DATABASE_URL's username carries that suffix (e.g.
        `postgres.<ref>`), it's copied onto the `sql_readonly` username too; a direct
        (non-pooled) connection's bare username is left as-is.
        """
        parsed = urlparse(self.database_url)
        username = "sql_readonly"
        if parsed.username and "." in parsed.username:
            _, project_ref = parsed.username.split(".", 1)
            username = f"sql_readonly.{project_ref}"
        netloc = f"{username}:{self.sql_readonly_password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


@lru_cache
def get_settings() -> Settings:
    return Settings()
