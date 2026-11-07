META_FILE = "db_meta.json"
DATA_DIR = "data"
ENCODING = "utf-8"
ID_COLUMN = "ID"
ID_TYPE = "int"
VALID_TYPES = {"int": int, "str": str, "bool": bool}
BOOLEAN_VALUES = {"true": True, "false": False}
CACHE_LIMIT = 128
TEMP_SUFFIX_BYTES = 8
COMMAND_PROMPT = ">>> Введите команду: "
CONFIRM_PROMPT = 'Вы уверены, что хотите выполнить "{}"? [y/n]: '
TABLE_NOT_FOUND = 'Таблица "{}" не существует.'
HELP_TEXT = (
    "\n***База данных***\n\n"
    "Управление таблицами\n"
    "  create_table <таблица> <столбец:тип> ...   |создать таблицу\n"
    "  list_tables                             |показать список таблиц\n"
    "  drop_table <таблица>                     |удалить таблицу\n"
    "  info <таблица>                           |показать схему и число записей\n\n"
    "Операции с данными\n"
    "  insert into <таблица> values (...)       |добавить запись\n"
    "  select from <таблица>                    |прочитать все записи\n"
    "  select from <таблица> where <столбец> = <значение>\n"
    "                                          |прочитать записи по условию\n"
    "  update <таблица> set <столбец> = <значение> "
    "where <столбец> = <значение>\n"
    "                                          |обновить записи\n"
    "  delete from <таблица> where <столбец> = <значение>\n"
    "                                          |удалить записи\n\n"
    "Общие команды\n"
    "  help                                    |показать справку\n"
    "  exit                                    |выйти\n"
)

type Value = str | int | bool
type Row = dict[str, Value]
type Clause = dict[str, Value]
type Schema = dict[str, str]
type Metadata = dict[str, Schema]
