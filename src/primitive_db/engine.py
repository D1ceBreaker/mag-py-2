import shlex

import prompt
from prettytable import PrettyTable

from . import core
from .constants import COMMAND_PROMPT, ID_COLUMN, META_FILE, Row, Schema
from .decorators import handle_db_errors
from .parser import parse_set, parse_values, parse_where, split_where
from .utils import (
    load_metadata,
    load_table_data,
    remove_table_data,
    save_metadata,
    save_table_data,
)

HELP_TEXT = """
***База данных***

Управление таблицами
  create_table <таблица> <столбец:тип> ...   создать таблицу
  list_tables                             показать список таблиц
  drop_table <таблица>                    удалить таблицу
  info <таблица>                          показать схему и число записей

Операции с данными
  insert into <таблица> values (...)      добавить запись
  select from <таблица> [where поле = значение]   прочитать записи
  update <таблица> set поле = значение where поле = значение
  delete from <таблица> where поле = значение

Общие команды
  help   показать справку
  exit   выйти
"""


def run() -> None:
    """Читает и выполняет команды до выхода из консоли."""
    print(HELP_TEXT)
    try:
        while True:
            command = prompt.string(COMMAND_PROMPT).strip()
            if command.lower() == "exit":
                break
            if command:
                _execute(command)
    except (EOFError, KeyboardInterrupt):
        print()


@handle_db_errors
def _execute(line: str) -> None:
    """Разбирает имя команды и передаёт аргументы обработчику."""
    command, *arguments = line.split(maxsplit=1)
    command = command.lower()
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Функции {command} нет. Попробуйте снова.")
        return
    handler(arguments[0] if arguments else "")


def _help(arguments: str) -> None:
    """Показывает синтаксис команд."""
    _require_count(arguments, 0, "help")
    print(HELP_TEXT)


def _create_table(arguments: str) -> None:
    """Создаёт пустую таблицу и сохраняет её схему."""
    parts = shlex.split(arguments)
    if len(parts) < 2:
        raise ValueError("Используйте create_table <таблица> <столбец:тип> ...")
    table_name, *columns = parts
    metadata = core.create_table(load_metadata(META_FILE), table_name, columns)
    if metadata is not None:
        save_table_data(table_name, [])
        save_metadata(META_FILE, metadata)
        columns_text = _format_schema(metadata[table_name])
        print(f'Таблица "{table_name}" успешно создана со столбцами: {columns_text}')


def _drop_table(arguments: str) -> None:
    """Удаляет схему и строки таблицы после подтверждения."""
    (table_name,) = _require_count(arguments, 1, "drop_table <таблица>")
    metadata = load_metadata(META_FILE)
    core.get_schema(metadata, table_name)
    updated_metadata = core.drop_table(metadata, table_name)
    if updated_metadata is not None:
        save_metadata(META_FILE, updated_metadata)
        remove_table_data(table_name)
        print(f'Таблица "{table_name}" успешно удалена.')


def _list_tables(arguments: str) -> None:
    """Выводит имена существующих таблиц."""
    _require_count(arguments, 0, "list_tables")
    metadata = load_metadata(META_FILE)
    if not metadata:
        print("Таблиц нет.")
    for table_name in metadata:
        print(f"- {table_name}")


def _info(arguments: str) -> None:
    """Показывает столбцы и количество строк таблицы."""
    (table_name,) = _require_count(arguments, 1, "info <таблица>")
    schema = _load_schema(table_name)
    print(f"Таблица: {table_name}")
    print(f"Столбцы: {_format_schema(schema)}")
    print(f"Количество записей: {len(load_table_data(table_name))}")


def _insert(arguments: str) -> None:
    """Добавляет строку и сохраняет таблицу."""
    header, separator, values_text = arguments.partition("(")
    syntax = "insert into <таблица> values (...)"
    into_keyword, table_name, values_keyword = _require_count(header, 3, syntax)
    if not separator or (into_keyword.lower(), values_keyword.lower()) != (
        "into",
        "values",
    ):
        raise ValueError(f"Используйте {syntax}")
    values = parse_values(separator + values_text)
    rows = core.insert(load_metadata(META_FILE), table_name, values)
    if rows is not None:
        save_table_data(table_name, rows)
        record_id = rows[-1][ID_COLUMN]
        print(f'Запись с ID={record_id} успешно добавлена в таблицу "{table_name}".')


def _select(arguments: str) -> None:
    """Выводит строки таблицы в порядке столбцов схемы."""
    table_name, condition_text = _from_arguments(arguments)
    schema = _load_schema(table_name)
    condition = parse_where(condition_text) if condition_text is not None else None
    rows = core.select(load_table_data(table_name), condition, schema=schema)
    if rows is not None:
        result = PrettyTable(list(schema))
        result.add_rows([[row[name] for name in schema] for row in rows])
        print(result)


def _update(arguments: str) -> None:
    """Изменяет строки таблицы по условию."""
    parts = arguments.split(maxsplit=2)
    syntax = "update <таблица> set <поле> = <значение> where <поле> = <значение>"
    if len(parts) != 3 or parts[1].lower() != "set":
        raise ValueError(f"Используйте {syntax}")
    table_name, _, assignments = parts
    set_clause, where_clause = split_where(assignments)
    if where_clause is None:
        raise ValueError(f"Используйте {syntax}")
    schema = _load_schema(table_name)
    condition = parse_where(where_clause)
    rows = load_table_data(table_name)
    updated_rows = core.update(rows, parse_set(set_clause), condition, schema=schema)
    if updated_rows is not None:
        affected = [row for row in rows if core.matches(row, condition)]
        _save_changes(table_name, updated_rows, affected, "обновлена")


def _delete(arguments: str) -> None:
    """Удаляет строки таблицы по условию после подтверждения."""
    table_name, condition_text = _from_arguments(arguments)
    if condition_text is None:
        raise ValueError("Для delete укажите условие where.")
    schema = _load_schema(table_name)
    condition = parse_where(condition_text)
    rows = load_table_data(table_name)
    updated_rows = core.delete(rows, condition, schema=schema)
    if updated_rows is not None:
        affected = [row for row in rows if core.matches(row, condition)]
        _save_changes(table_name, updated_rows, affected, "удалена")


def _require_count(arguments: str, count: int, syntax: str) -> list[str]:
    """Разбирает аргументы команды с фиксированным числом параметров."""
    parts = shlex.split(arguments)
    if len(parts) != count:
        raise ValueError(f"Используйте {syntax}")
    return parts


def _from_arguments(arguments: str) -> tuple[str, str | None]:
    """Разбирает имя таблицы и необязательное условие после from."""
    parts = arguments.split(maxsplit=3)
    if len(parts) >= 2 and parts[0].lower() == "from":
        if len(parts) == 2:
            return parts[1], None
        if len(parts) == 4 and parts[2].lower() == "where":
            return parts[1], parts[3]
    raise ValueError("Ожидается from <таблица> с условием where при необходимости.")


def _load_schema(table_name: str) -> Schema:
    """Читает схему указанной таблицы."""
    return core.get_schema(load_metadata(META_FILE), table_name)


def _format_schema(schema: Schema) -> str:
    """Форматирует столбцы для вывода в консоль."""
    return ", ".join(f"{name}:{type_name}" for name, type_name in schema.items())


def _save_changes(
    table_name: str, rows: list[Row], affected: list[Row], action: str
) -> None:
    """Сохраняет изменения и выводит идентификаторы затронутых строк."""
    if not affected:
        print("Подходящих записей нет.")
        return
    save_table_data(table_name, rows)
    for row in affected:
        print(
            f'Запись с ID={row[ID_COLUMN]} в таблице "{table_name}" успешно {action}.'
        )


COMMANDS = {
    "help": _help,
    "create_table": _create_table,
    "drop_table": _drop_table,
    "list_tables": _list_tables,
    "info": _info,
    "insert": _insert,
    "select": _select,
    "update": _update,
    "delete": _delete,
}
