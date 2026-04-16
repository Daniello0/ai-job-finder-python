from pathlib import Path
from typing import Any

from common.constants.parser import (
    DEFAULT_PAGES_TO_PARSE,
    DEFAULT_VACANCY_LIMIT,
    VACANCY_DETAILS_FILE,
    VACANCIES_FILE,
    VACANCY_LINKS_FILE,
)
from features.parser.clear_csv import process_csv
from features.parser.data_parser import parse_vacancy_details
from features.parser.url_parser import parse_vacancy_links


def has_data(file_path: Path) -> bool:
    """Return True when a CSV-like artifact exists and contains data rows."""
    return file_path.exists() and file_path.stat().st_size > 0


def orchestrate_parser_pipeline(
    pages_to_parse: int = DEFAULT_PAGES_TO_PARSE,
    vacancy_limit: int = DEFAULT_VACANCY_LIMIT,
    links_file: Path = VACANCY_LINKS_FILE,
    details_file: Path = VACANCY_DETAILS_FILE,
    cleaned_file: Path = VACANCIES_FILE,
) -> Any:
    """Run the full parser pipeline and return the cleaned vacancies data."""
    if not has_data(links_file):
        parse_vacancy_links(pages_to_parse=pages_to_parse, output_file=links_file)
    else:
        print(f"Использую существующий файл ссылок: {links_file}")

    parse_vacancy_details(
        input_file=links_file,
        output_file=details_file,
        limit=vacancy_limit,
    )
    return process_csv(input_file=details_file, output_file=cleaned_file)


if __name__ == "__main__":
    cleaned_data = orchestrate_parser_pipeline()
    preview = cleaned_data.head() if hasattr(cleaned_data, "head") else cleaned_data[:5]
    print(preview)
