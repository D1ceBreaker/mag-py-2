META_FILE = "db_meta.json"
DATA_DIR = "data"
ENCODING = "utf-8"
ID_COLUMN = "ID"
ID_TYPE = "int"
VALID_TYPES = {"int": int, "str": str, "bool": bool}
BOOLEAN_VALUES = {"true": True, "false": False}
CACHE_LIMIT = 128
COMMAND_PROMPT = ">>> Введите команду: "
CONFIRM_PROMPT = 'Вы уверены, что хотите выполнить "{}"? [y/n]: '
TABLE_NOT_FOUND = 'Таблица "{}" не существует.'

type Value = str | int | bool
type Row = dict[str, Value]
type Clause = dict[str, Value]
type Schema = dict[str, str]
type Metadata = dict[str, Schema]
