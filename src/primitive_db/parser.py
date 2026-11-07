from .constants import BOOLEAN_VALUES, Clause, Value

type Token = tuple[str, bool, int, int]


def _tokenize(text: str) -> list[Token]:
    """Разбить строку на слова и разделители с учётом кавычек."""
    tokens: list[Token] = []
    current: list[str] = []
    start = 0
    quote = ""
    quoted = False
    closed = False
    escaped = False

    for index, character in enumerate(text):
        if quote:
            if escaped:
                if character not in (quote, "\\"):
                    current.append("\\")
                current.append(character)
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
                closed = True
            else:
                current.append(character)
            continue

        if character in ("'", '"'):
            if current or closed:
                raise ValueError("Некорректное сочетание кавычек и значения")
            start = index
            quote = character
            quoted = True
        elif character in ",=()" or character.isspace():
            if current or closed:
                tokens.append(("".join(current), quoted, start, index))
                current = []
                quoted = False
                closed = False
            if not character.isspace():
                tokens.append((character, False, index, index + 1))
        else:
            if closed:
                raise ValueError("Некорректное сочетание кавычек и значения")
            if not current:
                start = index
            current.append(character)

    if quote:
        raise ValueError("Незакрытая строка в кавычках")
    if current or closed:
        tokens.append(("".join(current), quoted, start, len(text)))
    return tokens


def _parse_value(token: Token) -> Value:
    """Преобразовать значение в строку, целое число или bool."""
    value, quoted, _, _ = token
    if quoted:
        return value
    if value.lower() in BOOLEAN_VALUES:
        return BOOLEAN_VALUES[value.lower()]
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Некорректное значение: {value}") from error


def parse_values(text: str) -> list[Value]:
    """Прочитать список значений в круглых скобках."""
    tokens = _tokenize(text)
    if len(tokens) < 2 or tokens[0][:2] != ("(", False):
        raise ValueError("Ожидается список значений в круглых скобках")
    if tokens[-1][:2] != (")", False):
        raise ValueError("Ожидается список значений в круглых скобках")
    if len(tokens) == 2:
        return []

    values: list[Value] = []
    for index, token in enumerate(tokens[1:-1]):
        if index % 2:
            if token[0] != "," or token[1]:
                raise ValueError("Ожидается запятая между значениями")
        else:
            values.append(_parse_value(token))

    if len(tokens) % 2 == 0:
        raise ValueError("Ожидается значение после запятой")
    return values


def _parse_assignments(text: str) -> Clause:
    """Прочитать присваивания вида field = value через запятую."""
    tokens = _tokenize(text)
    if not tokens:
        raise ValueError("Условие не может быть пустым")

    assignments: Clause = {}
    for index in range(0, len(tokens), 4):
        part = tokens[index : index + 4]
        if len(part) < 3 or part[0][1] or not part[0][0].isidentifier():
            raise ValueError("Некорректное имя столбца")
        if part[1][0] != "=" or part[1][1]:
            raise ValueError("Ожидается знак равенства")
        if part[0][0] in assignments:
            raise ValueError(f"Столбец {part[0][0]} указан повторно")
        assignments[part[0][0]] = _parse_value(part[2])
        if len(part) == 4 and (part[3][0] != "," or part[3][1]):
            raise ValueError("Ожидается запятая между присваиваниями")
        if len(part) == 4 and index + 4 == len(tokens):
            raise ValueError("Ожидается присваивание после запятой")
    return assignments


def parse_where(text: str) -> Clause:
    """Разобрать условия выборки по столбцам."""
    return _parse_assignments(text)


def parse_set(text: str) -> Clause:
    """Разобрать обновления значений столбцов."""
    return _parse_assignments(text)


def split_where(text: str) -> tuple[str, str | None]:
    """Отделить непомещённое в кавычки слово where от команды."""
    tokens = _tokenize(text)
    for index, (token, quoted, start, end) in enumerate(tokens):
        is_assignment = tokens[index + 1 : index + 2]
        if token.lower() == "where" and not quoted:
            if is_assignment and is_assignment[0][:2] == ("=", False):
                continue
            return text[:start].strip(), text[end:].strip()
    return text.strip(), None
