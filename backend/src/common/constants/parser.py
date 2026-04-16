import os
from pathlib import Path


def get_env_int(name: str, default: int) -> int:
    """Read a positive integer from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from error
    if parsed_value <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return parsed_value


def get_env_float(name: str, default: float) -> float:
    """Read a positive float from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed_value = float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, got {value!r}.") from error
    if parsed_value <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return parsed_value


def get_env_str(name: str, default: str) -> str:
    """Read a non-empty string from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    stripped_value = value.strip()
    if not stripped_value:
        raise ValueError(f"{name} must not be empty.")
    return stripped_value


DEFAULT_ENCODING = "utf-8"
DEFAULT_CSV_ENCODING = "utf-8-sig"
DEFAULT_HTML_PARSER = "lxml"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SEARCH_BASE_URL = get_env_str("SEARCH_BASE_URL", "https://grodno.rabota.by/search/vacancy")
SEARCH_REFERER = "https://rabota.by/"
SEARCH_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
DETAIL_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,*/*;q=0.8"
)
ACCEPT_LANGUAGE = "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3"
CONNECTION_TYPE = "keep-alive"

SEARCH_PAGE_SIZE = get_env_int("SEARCH_PAGE_SIZE", 20)
SEARCH_TEXT = os.getenv("SEARCH_TEXT", "")
SEARCH_AREA = get_env_str("SEARCH_AREA", "1006")
SEARCH_SOURCE = get_env_str("SEARCH_SOURCE", "vacancy_search_list")
DEFAULT_START_PAGE = get_env_int("START_PAGE", 1) - 1
DEFAULT_PAGES_TO_PARSE = get_env_int("PAGES_TO_PARSE", 1)
DEFAULT_VACANCY_LIMIT = get_env_int("VACANCIES_COUNT", 3)

REQUEST_TIMEOUT_SECONDS = get_env_int("REQUEST_TIMEOUT_SECONDS", 15)
REQUEST_DELAY_MIN_SECONDS = get_env_float("REQUEST_DELAY_MIN_SECONDS", 2.0)
REQUEST_DELAY_MAX_SECONDS = get_env_float("REQUEST_DELAY_MAX_SECONDS", 5.0)
REQUEST_RETRY_COUNT = get_env_int("REQUEST_RETRY_COUNT", 3)
REQUEST_RETRY_BACKOFF_SECONDS = get_env_float("REQUEST_RETRY_BACKOFF_SECONDS", 2.0)

LINKS_HEADER = "Vacancy URL"
DETAILS_CSV_DELIMITER = ";"
MISSING_VALUE = "Не указано"
MISSING_SKILLS = "Не указаны"
MISSING_DESCRIPTION = "Нет описания"

DETAIL_FIELDS = [
    "title",
    "company",
    "salary",
    "payment_frequency",
    "experience",
    "employment",
    "hiring_format",
    "schedule",
    "hours",
    "work_format",
    "skills",
    "url",
    "description",
]

ORG_FORMS = ["ООО", "ИП", "УП", "ОАО", "ЗАО", "ЧУП", "СООО", "ОДО"]

BACKEND_DIR = Path(__file__).resolve().parents[3]
PUBLIC_DIR = BACKEND_DIR / "public"
VACANCY_LINKS_FILE = PUBLIC_DIR / "vacancy_links.csv"
VACANCY_DETAILS_FILE = PUBLIC_DIR / "vacancy_details.csv"
VACANCIES_FILE = PUBLIC_DIR / "vacancies.csv"
