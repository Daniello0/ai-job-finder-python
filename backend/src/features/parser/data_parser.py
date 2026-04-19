import csv
import random
import time
from pathlib import Path
from typing import Any

from common.constants.parser import (
    ACCEPT_LANGUAGE,
    CONNECTION_TYPE,
    DEFAULT_USER_AGENT,
    DEFAULT_CSV_ENCODING,
    DEFAULT_HTML_PARSER,
    DEFAULT_VACANCY_LIMIT,
    DETAIL_ACCEPT,
    DETAIL_FIELDS,
    DETAILS_CSV_DELIMITER,
    MISSING_DESCRIPTION,
    MISSING_SKILLS,
    MISSING_VALUE,
    REQUEST_DELAY_MAX_SECONDS,
    REQUEST_DELAY_MIN_SECONDS,
    REQUEST_RETRY_BACKOFF_SECONDS,
    REQUEST_RETRY_COUNT,
    REQUEST_TIMEOUT_SECONDS,
    SEARCH_REFERER,
    VACANCY_DETAILS_FILE,
    VACANCY_LINKS_FILE,
)
from common.utils.progress import track_progress


def get_headers(user_agent: str) -> dict[str, str]:
    """Build headers for vacancy details requests."""
    return {
        "User-Agent": user_agent,
        "Accept": DETAIL_ACCEPT,
        "Accept-Language": ACCEPT_LANGUAGE,
        "Connection": CONNECTION_TYPE,
        "Referer": SEARCH_REFERER,
    }


def get_text_safe(soup: Any, selector: str, attribute: str = "data-qa") -> str:
    """Safely extract text from a BeautifulSoup document."""
    tag = soup.find(attrs={attribute: selector})
    return tag.get_text(strip=True) if tag else MISSING_VALUE


def parse_skills(soup: Any) -> str:
    """Extract vacancy skills as a comma-separated string."""
    skills_tags = soup.find_all("li", {"data-qa": "skills-element"})
    if not skills_tags:
        return MISSING_SKILLS
    return ", ".join(skill.get_text(strip=True) for skill in skills_tags)


def parse_description(soup: Any) -> str:
    """Extract the vacancy description from the page."""
    description_tag = soup.find("div", {"data-qa": "vacancy-description"})
    if not description_tag:
        return MISSING_DESCRIPTION
    return description_tag.get_text(separator=" ").strip()


def build_user_agent() -> str:
    """Return a stable User-Agent with a fake-useragent fallback."""
    try:
        from fake_useragent import UserAgent

        return UserAgent().random
    except Exception:
        return DEFAULT_USER_AGENT


def fetch_vacancy_page(url: str, user_agent: str) -> str | None:
    """Fetch one vacancy page with retries."""
    import requests

    for attempt in range(1, REQUEST_RETRY_COUNT + 1):
        try:
            response = requests.get(
                url,
                headers=get_headers(user_agent),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as error:
            if attempt == REQUEST_RETRY_COUNT:
                print(f"Не удалось загрузить вакансию {url}: {error}")
                return None
            wait_time = REQUEST_RETRY_BACKOFF_SECONDS * attempt
            print(
                f"Ошибка загрузки вакансии {url} "
                f"(попытка {attempt}/{REQUEST_RETRY_COUNT}): {error}. "
                f"Повтор через {wait_time:.1f} сек."
            )
            time.sleep(wait_time)
    return None


def parse_vacancy(url: str, user_agent: str) -> dict[str, str] | None:
    """Parse one vacancy page and return a normalized row."""
    from bs4 import BeautifulSoup

    response_text = fetch_vacancy_page(url, user_agent)
    if response_text is None:
        return None
    soup = BeautifulSoup(response_text, DEFAULT_HTML_PARSER)
    return {
        "title": get_text_safe(soup, "vacancy-title"),
        "company": get_text_safe(soup, "vacancy-company-name"),
        "salary": get_text_safe(soup, "vacancy-salary"),
        "payment_frequency": get_text_safe(soup, "compensation-frequency-text"),
        "experience": get_text_safe(soup, "vacancy-experience"),
        "employment": get_text_safe(soup, "common-employment-text"),
        "hiring_format": get_text_safe(soup, "vacancy-hiring-formats"),
        "schedule": get_text_safe(soup, "work-schedule-by-days-text"),
        "hours": get_text_safe(soup, "working-hours-text"),
        "work_format": get_text_safe(soup, "work-formats-text"),
        "skills": parse_skills(soup),
        "url": url,
        "description": parse_description(soup),
    }


def read_vacancy_urls(
    input_file: Path = VACANCY_LINKS_FILE,
    limit: int | None = DEFAULT_VACANCY_LIMIT,
) -> list[str]:
    """Read vacancy URLs from the links CSV file."""
    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл {input_file} не найден. Сначала запустите сбор ссылок."
        )
    with input_file.open("r", encoding=DEFAULT_CSV_ENCODING) as file:
        reader = csv.reader(file, delimiter=DETAILS_CSV_DELIMITER)
        next(reader, None)
        urls = [row[0] for row in reader if row]
    return urls[:limit] if limit else urls


def read_existing_details(output_file: Path) -> list[dict[str, str]]:
    """Read already parsed vacancy rows if the file exists."""
    if not output_file.exists():
        return []
    with output_file.open("r", encoding=DEFAULT_CSV_ENCODING) as file:
        reader = csv.DictReader(file, delimiter=DETAILS_CSV_DELIMITER)
        return [row for row in reader if row.get("url")]


def save_vacancy_details(
    rows: list[dict[str, str]],
    output_file: Path = VACANCY_DETAILS_FILE,
) -> Path:
    """Save parsed vacancy rows into the details CSV file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding=DEFAULT_CSV_ENCODING) as file:
        writer = csv.DictWriter(
            file, fieldnames=DETAIL_FIELDS, delimiter=DETAILS_CSV_DELIMITER
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_file


def parse_vacancy_details(
    input_file: Path = VACANCY_LINKS_FILE,
    output_file: Path = VACANCY_DETAILS_FILE,
    limit: int | None = DEFAULT_VACANCY_LIMIT,
) -> list[dict[str, str]]:
    """Parse vacancy details from saved links and write them to CSV."""
    urls = read_vacancy_urls(input_file, limit)
    print(f"Загружено {len(urls)} ссылок. Начинаю парсинг...")
    user_agent = build_user_agent()
    rows = read_existing_details(output_file)
    processed_urls = {row["url"] for row in rows if row.get("url")}
    pending_urls = [url for url in urls if url not in processed_urls]
    if not pending_urls:
        print(f"Все {len(urls)} вакансий уже обработаны.")
        return rows
    for url in track_progress(
        pending_urls, total=len(pending_urls), description="Сбор данных"
    ):
        row = parse_vacancy(url, user_agent)
        if row is None:
            continue
        rows.append(row)
        save_vacancy_details(rows, output_file)
        time.sleep(random.uniform(REQUEST_DELAY_MIN_SECONDS, REQUEST_DELAY_MAX_SECONDS))
    if not rows:
        raise ValueError("Не удалось собрать данные по вакансиям.")
    print(f"\nГотово! Данные сохранены в {output_file}")
    return rows


if __name__ == "__main__":
    parse_vacancy_details()
