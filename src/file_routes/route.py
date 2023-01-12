from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def route(
    name: str | None = None,
    default: dict[str, Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = function(*args, **kwargs)
            return result

        return wrapper

    return decorator
