import time
from typing import Any, Callable

from .constants import CACHE_LIMIT, CONFIRM_PROMPT


def handle_db_errors(operation: Callable) -> Callable:
    """Выводит ошибки базы данных и возвращает None при сбое."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return operation(*args, **kwargs)
        except FileNotFoundError:
            print("Ошибка: Файл данных не найден.")
        except KeyError as error:
            print(f"Ошибка: {error.args[0]}")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлами: {error}")
        return None

    return wrapper


def confirm_action(action_name: str) -> Callable:
    """Создаёт декоратор для подтверждения опасной операции."""

    def decorate(operation: Callable) -> Callable:
        """Запрашивает подтверждение перед вызовом операции."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if input(CONFIRM_PROMPT.format(action_name)) != "y":
                print("Операция отменена.")
                return None
            return operation(*args, **kwargs)

        return wrapper

    return decorate


def log_time(operation: Callable) -> Callable:
    """Измеряет длительность вызова функции."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started_at = time.monotonic()
        try:
            return operation(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started_at
            print(f"Функция {operation.__name__} выполнилась за {elapsed:.3f} секунд")

    return wrapper


def create_cacher() -> Callable:
    """Создаёт функцию, которая хранит результаты вызовов по ключу."""

    cache: dict[object, Any] = {}

    def cache_result(key: object, value_func: Callable) -> Any:
        if key not in cache:
            result = value_func()
            if len(cache) >= CACHE_LIMIT:
                del cache[next(iter(cache))]
            cache[key] = result
        return cache[key]

    return cache_result
