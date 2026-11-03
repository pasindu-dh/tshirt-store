from collections import deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    """In-memory failed-login limiter.

    Suitable for a single process. Multi-worker deployments should use a
    shared store such as Redis.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts.get(key)

        if attempts is None:
            return deque()

        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()

        if not attempts:
            self._attempts.pop(key, None)

        return attempts

    def retry_after(self, key: str) -> int:
        now = monotonic()

        with self._lock:
            attempts = self._recent(key, now)

            if len(attempts) < self.max_attempts:
                return 0

            remaining = self.window_seconds - (now - attempts[0])
            return max(1, int(remaining) + 1)

    def record_failure(self, key: str) -> None:
        now = monotonic()

        with self._lock:
            attempts = self._recent(key, now)
            attempts.append(now)
            self._attempts[key] = attempts

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


login_account_limiter = LoginRateLimiter(
    max_attempts=5, window_seconds=15 * 60
)
login_ip_limiter = LoginRateLimiter(
    max_attempts=20, window_seconds=15 * 60
)
