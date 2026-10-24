"""Rate limit simple en memoria para el login.

Suficiente para el MVP de un solo proceso. En producción con varios workers
se debe reemplazar por Redis o similar.
"""

import time
from collections import defaultdict


class LoginRateLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str) -> None:
        cutoff = time.monotonic() - self.window_seconds
        self._attempts[key] = [ts for ts in self._attempts[key] if ts > cutoff]

    def is_blocked(self, key: str, limit: int) -> bool:
        self._prune(key)
        return len(self._attempts[key]) >= limit

    def register_failure(self, key: str) -> None:
        self._prune(key)
        self._attempts[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()


login_limiter = LoginRateLimiter()
