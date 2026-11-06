from typing import Callable

from .constants import (
    ID_COLUMN,
    ID_TYPE,
    TABLE_NOT_FOUND,
    VALID_TYPES,
    Clause,
    Metadata,
    Row,
    Schema,
    Value,
)
from .decorators import confirm_action, create_cacher, handle_db_errors, log_time
from .utils import load_table_data

type ScalarKey = tuple[type, Value]
type RowKey = tuple[tuple[str, ScalarKey], ...]
type QueryKey = tuple[tuple[RowKey, ...], RowKey]

SELECT_CACHE: Callable[[QueryKey, Callable[[], tuple[int, ...]]], tuple[int, ...]] = (
    create_cacher()
)


@handle_db_errors
def create_table(metadata: Metadata, table_name: str, columns: list[str]) -> Metadata:
    """Добавляет в метаданные схему с обязательным столбцом ID."""
    if any(name.casefold() == table_name.casefold() for name in metadata):
        raise KeyError(f'Таблица "{table_name}" уже существует.')
    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}.")
    schema: Schema = {ID_COLUMN: ID_TYPE}
    declared_columns: set[str] = set()
    for definition in columns:
        name, separator, type_name = definition.partition(":")
        if not separator or not name.isidentifier() or type_name not in VALID_TYPES:
            raise ValueError(f"Некорректное определение столбца: {definition}.")
        if name in declared_columns:
            raise ValueError(f'Столбец "{name}" указан несколько раз.')
        if name == ID_COLUMN and type_name != ID_TYPE:
            raise ValueError(f"Столбец {ID_COLUMN} должен иметь тип {ID_TYPE}.")
        declared_columns.add(name)
        schema[name] = type_name
    return {**metadata, table_name: schema}


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata: Metadata, table_name: str) -> Metadata:
    """Возвращает метаданные без указанной таблицы."""
    get_schema(metadata, table_name)
    return {name: schema for name, schema in metadata.items() if name != table_name}


@handle_db_errors
@log_time
def insert(metadata: Metadata, table_name: str, values: list[Value]) -> list[Row]:
    """Добавляет строку с ID, следующим за максимальным в таблице."""
    schema = get_schema(metadata, table_name)
    columns = [name for name in schema if name != ID_COLUMN]
    if len(values) != len(columns):
        raise ValueError(
            f"Ожидалось значений: {len(columns)}, получено: {len(values)}."
        )
    record = dict(zip(columns, values, strict=True))
    _validate_clause(schema, record)
    rows = load_table_data(table_name)
    next_id = max((int(row[ID_COLUMN]) for row in rows), default=0) + 1
    return [*rows, {ID_COLUMN: next_id, **record}]


@handle_db_errors
@log_time
def select(
    table_data: list[Row],
    where_clause: Clause | None = None,
    *,
    schema: Schema | None = None,
) -> list[Row]:
    """Возвращает строки по условию и кэширует индексы совпадений."""
    condition = where_clause or {}
    if schema is not None:
        _validate_clause(schema, condition)
    key = (tuple(_row_key(row) for row in table_data), _row_key(condition))

    def matching_indices() -> tuple[int, ...]:
        """Собирает индексы строк, которые подходят под условие."""
        return tuple(
            index for index, row in enumerate(table_data) if matches(row, condition)
        )

    return [table_data[index].copy() for index in SELECT_CACHE(key, matching_indices)]


@handle_db_errors
def update(
    table_data: list[Row],
    set_clause: Clause,
    where_clause: Clause,
    *,
    schema: Schema | None = None,
) -> list[Row]:
    """Возвращает строки с обновлёнными значениями."""
    if not where_clause:
        raise ValueError("Для update укажите условие where.")
    if ID_COLUMN in set_clause:
        raise ValueError(f"Столбец {ID_COLUMN} нельзя обновить.")
    if schema is not None:
        _validate_clause(schema, set_clause)
        _validate_clause(schema, where_clause)
    return [
        {**row, **set_clause} if matches(row, where_clause) else row
        for row in table_data
    ]


@handle_db_errors
@confirm_action("удаление записи")
def delete(
    table_data: list[Row],
    where_clause: Clause,
    *,
    schema: Schema | None = None,
) -> list[Row]:
    """Возвращает строки, которые не подходят под условие удаления."""
    if not where_clause:
        raise ValueError("Для delete укажите условие where.")
    if schema is not None:
        _validate_clause(schema, where_clause)
    return [row for row in table_data if not matches(row, where_clause)]


def get_schema(metadata: Metadata, table_name: str) -> Schema:
    """Возвращает схему таблицы или сообщает об отсутствии таблицы."""
    if table_name not in metadata:
        raise KeyError(TABLE_NOT_FOUND.format(table_name))
    return metadata[table_name]


def matches(row: Row, clause: Clause) -> bool:
    """Сопоставляет значения и их типы с условием."""
    return all(
        type(row[name]) is type(value) and row[name] == value
        for name, value in clause.items()
    )


def _validate_clause(schema: Schema, clause: Clause) -> None:
    """Проверяет имена и типы столбцов."""
    for name, value in clause.items():
        if name not in schema:
            raise KeyError(f'Столбец "{name}" не найден.')
        expected_type = schema[name]
        if type(value) is not VALID_TYPES[expected_type]:
            raise ValueError(f'Столбец "{name}" ожидает значение типа {expected_type}.')


def _row_key(row: Row) -> RowKey:
    """Преобразует словарь в ключ кэша с учётом типов значений."""
    return tuple((name, (type(value), value)) for name, value in sorted(row.items()))
