import json
import os

from .constants import DATA_DIR, ENCODING, TEMP_SUFFIX_BYTES, Metadata, Row


def load_metadata(filepath: str) -> Metadata:
    """Читает схемы таблиц из JSON."""
    try:
        with open(filepath, encoding=ENCODING) as source:
            return json.load(source)
    except FileNotFoundError:
        return {}


def save_metadata(filepath: str, data: Metadata) -> None:
    """Сохраняет схемы таблиц в JSON."""
    _save_json(filepath, data)


def load_table_data(table_name: str) -> list[Row]:
    """Читает строки таблицы, считая отсутствующий файл пустой таблицей."""
    try:
        with open(_table_path(table_name), encoding=ENCODING) as source:
            return json.load(source)
    except FileNotFoundError:
        return []


def save_table_data(table_name: str, data: list[Row]) -> None:
    """Сохраняет строки таблицы в отдельном JSON-файле."""
    os.makedirs(DATA_DIR, exist_ok=True)
    _save_json(_table_path(table_name), data)


def remove_table_data(table_name: str) -> None:
    """Удаляет файл строк, если он существует."""
    try:
        os.remove(_table_path(table_name))
    except FileNotFoundError:
        return


def _table_path(table_name: str) -> str:
    """Строит путь к файлу строк таблицы."""
    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}.")
    return os.path.join(DATA_DIR, f"{table_name}.json")


def _save_json(filepath: str, data: Metadata | list[Row]) -> None:
    """Заменяет JSON-файл после успешной записи временного файла."""
    temporary_path = f"{filepath}.{os.urandom(TEMP_SUFFIX_BYTES).hex()}.tmp"
    try:
        with open(temporary_path, "x", encoding=ENCODING) as destination:
            json.dump(data, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
        os.replace(temporary_path, filepath)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
