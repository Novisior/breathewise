"""A tiny in-memory cache where every entry expires after `ttl_seconds`."""
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: int, max_items: int = 500,
                 clock: Callable[[], float] = time.monotonic):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._clock = clock  # injectable so tests don't need to sleep
        self._data: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._clock() >= expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: Any, value: Any) -> None:
        if len(self._data) >= self.max_items and key not in self._data:
            self._evict()
        self._data[key] = (self._clock() + self.ttl, value)

    def clear(self) -> None:
        self._data.clear()

    def _evict(self) -> None:
        now = self._clock()
        for k in [k for k, (exp, _) in self._data.items() if exp <= now]:
            del self._data[k]
        if len(self._data) >= self.max_items:  # still full: drop the oldest entry
            oldest = min(self._data, key=lambda k: self._data[k][0])
            del self._data[oldest]
