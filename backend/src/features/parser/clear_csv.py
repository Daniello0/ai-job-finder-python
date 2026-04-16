import re
import csv
from pathlib import Path
from typing import Any

from common.constants.parser import (
    DEFAULT_CSV_ENCODING,
    DETAILS_CSV_DELIMITER,
    ORG_FORMS,
    VACANCIES_FILE,
    VACANCY_DETAILS_FILE,
)
from common.utils.progress import track_progress

FIELD_PREFIXES = {
    "hiring_format": "Оформление:",
    "schedule": "График:",
    "hours": "Рабочие часы:",
    "work_format": "Формат работы:",
    "payment_frequency": "Выплаты:",
}


def clean_text(text: Any) -> str:
    """Normalize text values before exporting the cleaned CSV."""
    if not text:
        return ""
    text = str(text)

    # 1. Убираем лишние переносы строк и табуляцию внутри ячеек
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")

    # 2. Разлепляем слипшиеся слова и цифры
    # Пример: "от1 000до1 400Brза месяц" -> "от 1 000 до 1 400 Br за месяц"

    # Добавляем пробел между цифрой и буквой (1000Br -> 1000 Br)
    text = re.sub(r"(\d)([А-Яа-яA-Za-z])", r"\1 \2", text)
    # Добавляем пробел между буквой и цифрой (от1000 -> от 1000)
    text = re.sub(r"([А-Яа-яA-Za-z])(\d)", r"\1 \2", text)
    # Исправляем "Brза" -> "Br за"
    text = re.sub(r"(Br)(за)", r"\1 \2", text, flags=re.IGNORECASE)
    # Исправляем "месяцдо" -> "месяц до"
    text = re.sub(r"(месяц)(до)", r"\1 \2", text, flags=re.IGNORECASE)
    # Исправляем "месяцна" -> "месяц на"
    text = re.sub(r"(месяц)(на)", r"\1 \2", text, flags=re.IGNORECASE)

    # Исправляем слипшиеся организационные формы (ОООНутри -> ООО Нутри)
    for form in ORG_FORMS:
        text = re.sub(rf"^({form})([А-ЯЁA-Z])", r"\1 \2", text)

    # 3. Убираем двойные пробелы
    text = re.sub(r"\s+", " ", text).strip()

    return text


def strip_field_prefix(field: str, text: str) -> str:
    """Remove duplicated technical prefixes from selected fields."""
    prefix = FIELD_PREFIXES.get(field)
    if not prefix:
        return text
    cleaned = text
    while cleaned.startswith(prefix):
        cleaned = cleaned.removeprefix(prefix).strip()
    return cleaned.rstrip(";").strip()


def capitalize_first_letter(text: str) -> str:
    """Capitalize only the first character and keep the rest unchanged."""
    if not text:
        return text
    return text[0].upper() + text[1:]


def clean_row(row: dict[str, str]) -> dict[str, str]:
    """Clean every value in a parsed CSV row."""
    cleaned_row: dict[str, str] = {}
    for key, value in row.items():
        if key == "url":
            cleaned_row[key] = "" if value is None else str(value).strip()
            continue
        cleaned_value = clean_text(value)
        cleaned_value = strip_field_prefix(key, cleaned_value)
        cleaned_row[key] = capitalize_first_letter(cleaned_value)
    return cleaned_row


def process_csv_with_pandas(input_file: Path, output_file: Path) -> Any:
    """Clean a CSV file with pandas when the dependency is available."""
    import pandas as pd
    from tqdm import tqdm

    dataframe = pd.read_csv(
        input_file,
        sep=DETAILS_CSV_DELIMITER,
        encoding=DEFAULT_CSV_ENCODING,
    )
    if dataframe.empty:
        raise ValueError("Файл пуст или не удалось прочитать данные.")
    tqdm.pandas(desc="Очистка данных")
    cleaned_dataframe = (
        dataframe.fillna("")
        .astype(str)
        .progress_apply(
            lambda column: column.map(str.strip)
            if column.name == "url"
            else column.map(clean_text)
            .map(lambda value: strip_field_prefix(column.name, value))
            .map(capitalize_first_letter)
        )
    )
    cleaned_dataframe.to_csv(
        output_file,
        sep=DETAILS_CSV_DELIMITER,
        index=False,
        encoding=DEFAULT_CSV_ENCODING,
    )
    return cleaned_dataframe


def process_csv_with_csv(input_file: Path, output_file: Path) -> list[dict[str, str]]:
    """Clean a CSV file with the standard library."""
    with input_file.open("r", encoding=DEFAULT_CSV_ENCODING) as file:
        reader = csv.DictReader(file, delimiter=DETAILS_CSV_DELIMITER)
        raw_rows = list(reader)
        cleaned_rows = [
            clean_row(row)
            for row in track_progress(
                raw_rows,
                total=len(raw_rows),
                description="Очистка данных",
            )
        ]
        fieldnames = reader.fieldnames
    if not cleaned_rows or not fieldnames:
        raise ValueError("Файл пуст или не удалось прочитать данные.")
    with output_file.open("w", newline="", encoding=DEFAULT_CSV_ENCODING) as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames, delimiter=DETAILS_CSV_DELIMITER
        )
        writer.writeheader()
        writer.writerows(cleaned_rows)
    return cleaned_rows


def process_csv(
    input_file: Path = VACANCY_DETAILS_FILE,
    output_file: Path = VACANCIES_FILE,
) -> Any:
    """Clean parsed vacancy data with pandas when available, else with csv."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        cleaned_data = process_csv_with_pandas(input_file, output_file)
    except ModuleNotFoundError:
        cleaned_data = process_csv_with_csv(input_file, output_file)
    print(f"Очистка завершена! Файл сохранен как: {output_file}")
    return cleaned_data


if __name__ == "__main__":
    process_csv()
