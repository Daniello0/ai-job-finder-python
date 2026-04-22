import os

from common.constants.database import (
    DEFAULT_DB_HOST,
    DEFAULT_DB_NAME,
    DEFAULT_DB_PASSWORD,
    DEFAULT_DB_PORT,
    DEFAULT_DB_USER,
)


def _get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped_value = value.strip()
    if not stripped_value:
        raise ValueError(f"{name} must not be empty.")
    return stripped_value


def build_database_url() -> str:
    """Build an async SQLAlchemy database URL from env variables.

    Priority:
    - DATABASE_URL (full DSN)
    - DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME
    """

    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.strip():
        return database_url.strip()

    host = _get_env_str("DB_HOST", DEFAULT_DB_HOST)
    port = _get_env_str("DB_PORT", DEFAULT_DB_PORT)
    user = _get_env_str("DB_USER", DEFAULT_DB_USER)
    password = _get_env_str("DB_PASSWORD", DEFAULT_DB_PASSWORD)
    db_name = _get_env_str("DB_NAME", DEFAULT_DB_NAME)

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
