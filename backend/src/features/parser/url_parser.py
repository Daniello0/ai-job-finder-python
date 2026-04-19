import csv
import random
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from common.constants.parser import (
    DEFAULT_USER_AGENT,
    DEFAULT_CSV_ENCODING,
    DEFAULT_HTML_PARSER,
    DEFAULT_PAGES_TO_PARSE,
    DEFAULT_START_PAGE,
    DETAILS_CSV_DELIMITER,
    LINKS_HEADER,
    REQUEST_DELAY_MAX_SECONDS,
    REQUEST_DELAY_MIN_SECONDS,
    REQUEST_RETRY_BACKOFF_SECONDS,
    REQUEST_RETRY_COUNT,
    REQUEST_TIMEOUT_SECONDS,
    SEARCH_ACCEPT,
    SEARCH_AREA,
    SEARCH_BASE_URL,
    SEARCH_PAGE_SIZE,
    SEARCH_SOURCE,
    SEARCH_TEXT,
    VACANCY_LINKS_FILE,
)
from common.utils.progress import track_progress


def normalize_vacancy_link(url: str) -> str:
    """Drop query params and fragments from vacancy links."""
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"


def is_valid_vacancy_link(url: str) -> bool:
    """Keep only direct rabota.by vacancy links."""
    normalized_url = normalize_vacancy_link(url)
    return "rabota.by/vacancy/" in normalized_url


def extract_vacancy_links(items: list[Any]) -> list[str]:
    """Extract unique direct vacancy links from parsed HTML items."""
    unique_links: list[str] = []
    seen_links: set[str] = set()
    for item in items:
        href = item.get("href")
        if not href:
            continue
        normalized_url = normalize_vacancy_link(href)
        if normalized_url in seen_links or not is_valid_vacancy_link(normalized_url):
            continue
        seen_links.add(normalized_url)
        unique_links.append(normalized_url)
    return unique_links


def build_search_params(page: int) -> dict[str, str | int]:
    """Build request params for the vacancy search page."""
    return {
        "text": SEARCH_TEXT,
        "salary": "",
        "ored_clusters": "true",
        "items_on_page": str(SEARCH_PAGE_SIZE),
        "area": SEARCH_AREA,
        "hhtmFrom": SEARCH_SOURCE,
        "page": page,
    }


def build_search_headers(user_agent: str) -> dict[str, str]:
    """Build headers for vacancy search requests."""
    return {
        "User-Agent": user_agent,
        "Accept": SEARCH_ACCEPT,
    }


def build_user_agent() -> str:
    """Return a stable User-Agent with a fake-useragent fallback."""
    try:
        from fake_useragent import UserAgent

        return UserAgent().random
    except Exception:
        return DEFAULT_USER_AGENT


def request_search_page(page: int, user_agent: str) -> str | None:
    """Fetch one search page with retries."""
    import requests

    for attempt in range(1, REQUEST_RETRY_COUNT + 1):
        try:
            response = requests.get(
                SEARCH_BASE_URL,
                params=build_search_params(page),
                headers=build_search_headers(user_agent),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as error:
            if attempt == REQUEST_RETRY_COUNT:
                print(f"Не удалось загрузить страницу {page + 1}: {error}")
                return None
            wait_time = REQUEST_RETRY_BACKOFF_SECONDS * attempt
            print(
                f"Ошибка загрузки страницы {page + 1} "
                f"(попытка {attempt}/{REQUEST_RETRY_COUNT}): {error}. "
                f"Повтор через {wait_time:.1f} сек."
            )
            time.sleep(wait_time)
    return None


def parse_search_page(page: int, user_agent: str) -> list[str] | None:
    """Parse a single search results page and return vacancy links."""
    from bs4 import BeautifulSoup

    response_text = request_search_page(page, user_agent)
    if response_text is None:
        return None
    soup = BeautifulSoup(response_text, DEFAULT_HTML_PARSER)
    items = soup.find_all("a", {"data-qa": "serp-item__title"})
    return extract_vacancy_links(items)


def save_links_to_csv(links: list[str], output_file: Path = VACANCY_LINKS_FILE) -> Path:
    """Save parsed vacancy links into a CSV file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding=DEFAULT_CSV_ENCODING) as file:
        writer = csv.writer(file, delimiter=DETAILS_CSV_DELIMITER)
        writer.writerow([LINKS_HEADER])
        writer.writerows([[link] for link in links])
    return output_file


def read_existing_links(input_file: Path) -> list[str]:
    """Read already saved vacancy links if the file exists."""
    if not input_file.exists():
        return []
    with input_file.open("r", encoding=DEFAULT_CSV_ENCODING) as file:
        reader = csv.reader(file, delimiter=DETAILS_CSV_DELIMITER)
        next(reader, None)
        return [row[0] for row in reader if row and row[0]]


def parse_vacancy_links(
    pages_to_parse: int = DEFAULT_PAGES_TO_PARSE,
    output_file: Path = VACANCY_LINKS_FILE,
    start_page: int = DEFAULT_START_PAGE,
) -> list[str]:
    """Collect vacancy links from search pages and save them to CSV."""
    user_agent = build_user_agent()
    all_links = read_existing_links(output_file)
    seen_links = set(all_links)
    pages = range(start_page, start_page + pages_to_parse)
    for page in track_progress(
        pages,
        total=pages_to_parse,
        description="Сбор url",
    ):
        page_links = parse_search_page(page, user_agent)
        if page_links is None:
            print(
                f"Страница {page + 1} пропущена: запрос не удался даже после повторов."
            )
            continue
        if not page_links:
            print(f"Вакансии на странице {page + 1} не найдены. Завершаем сбор.")
            break
        new_links = [link for link in page_links if link not in seen_links]
        if not new_links:
            print(f"На странице {page + 1} новых ссылок не найдено.")
            continue
        all_links.extend(new_links)
        seen_links.update(new_links)
        save_links_to_csv(all_links, output_file)
        wait_time = random.uniform(REQUEST_DELAY_MIN_SECONDS, REQUEST_DELAY_MAX_SECONDS)
        time.sleep(wait_time)
    if not all_links:
        raise ValueError("Список ссылок пуст, сохранять нечего.")
    print(f"\nГотово! Сохранено {len(all_links)} ссылок в файл {output_file}")
    return all_links


if __name__ == "__main__":
    parse_vacancy_links()
