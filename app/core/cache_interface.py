"""Cache provider interface for Mizan.

Domains should depend on this abstraction, not on a specific provider.
The default provider uses Redis, but future implementations can plug in
alternatives without changing business logic.
"""

from typing import Any


class CacheProvider:
    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def invalidate_pattern(self, pattern: str) -> None:
        raise NotImplementedError


class NullCacheProvider(CacheProvider):
    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def invalidate_pattern(self, pattern: str) -> None:
        pass


cache_provider: CacheProvider = NullCacheProvider()
