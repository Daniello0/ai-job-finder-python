import os


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

    host = _get_env_str("DB_HOST", "localhost")
    port = _get_env_str("DB_PORT", "5432")
    user = _get_env_str("DB_USER", "postgres")
    password = _get_env_str("DB_PASSWORD", "postgres")
    db_name = _get_env_str("DB_NAME", "ai_job_finder")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
