from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitBreaker:
    def __init__(
        self,
        action: Callable[..., T],
        name: str,
        fallback: Callable[[], Any] | None = None,
    ) -> None:
        self._action = action
        self._name = name
        self._fallback = fallback or (lambda: None)
        self.opened = False

    def fire(self, *args: Any, **kwargs: Any) -> T | Any:
        try:
            result = self._action(*args, **kwargs)
            self.opened = False
            return result
        except Exception:
            self.opened = True
            print(f"Circuit breaker fallback triggered for {self._name}")
            return self._fallback()


def with_circuit_breaker(
    action: Callable[..., T],
    name: str,
    fallback: Callable[[], Any] | None = None,
) -> CircuitBreaker:
    return CircuitBreaker(action, name, fallback)


def with_retry(action: Callable[[], T], name: str, attempts: int = 3, delay_seconds: float = 0.5) -> T:
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"{name} attempt {attempt}/{attempts} failed: {error_message(error)}")
            if attempt < attempts:
                time.sleep(delay_seconds * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"{name} failed without an exception")


def resilient_call(name: str, action: Callable[[], T], fallback: T | None = None) -> T:
    breaker = with_circuit_breaker(lambda: with_retry(action, name), name)
    result = breaker.fire()

    if result is None:
        if fallback is not None:
            return fallback
        raise RuntimeError(f"Circuit breaker fallback triggered for {name}")

    return result


def error_message(error: BaseException) -> str:
    return str(error)
