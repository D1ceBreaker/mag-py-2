import time
from typing import Callable

from .constants import CACHE_LIMIT, CONFIRM_PROMPT


def handle_db_errors[**P, R](operation: Callable[P, R]) -> Callable[P, R | None]:
    """Выводит ошибки базы данных и возвращает None при сбое."""

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        """Выполняет операцию с обработкой ошибок."""
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


def confirm_action[**P, R](
    action_name: str,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Создаёт декоратор для подтверждения опасной операции."""

    def decorate(operation: Callable[P, R]) -> Callable[P, R | None]:
        """Запрашивает подтверждение перед вызовом операции."""

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            """Выполняет действие только после ответа y."""
            if input(CONFIRM_PROMPT.format(action_name)) != "y":
                print("Операция отменена.")
                return None
            return operation(*args, **kwargs)

        return wrapper

    return decorate


def log_time[**P, R](operation: Callable[P, R]) -> Callable[P, R]:
    """Измеряет длительность вызова функции."""

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        """Выводит длительность вызова в секундах."""
        started_at = time.monotonic()
        try:
            return operation(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started_at
            print(f"Функция {operation.__name__} выполнилась за {elapsed:.3f} секунд")

    return wrapper


def create_cacher[K, R]() -> Callable[[K, Callable[[], R]], R]:
    """Создаёт функцию, которая хранит результаты вызовов по ключу."""
    cache: dict[K, R] = {}

    def cache_result(key: K, value_func: Callable[[], R]) -> R:
        """Вычисляет результат при первом обращении к ключу."""
        if key not in cache:
            result = value_func()
            if len(cache) >= CACHE_LIMIT:
                del cache[next(iter(cache))]
            cache[key] = result
        return cache[key]

    return cache_result
