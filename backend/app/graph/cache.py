"""
Query result caching layer for expensive Neo4j governance traversals.

Caches deterministic graph traversals with TTL to reduce database load
on frequently-accessed paths (roles → training roadmaps).

Cache is cleared on seed_graph re-run (via cache_invalidate()).
"""

import time
import hashlib
from typing import Any, Callable, Optional
from functools import wraps


class QueryCache:
    """Simple in-memory cache for Neo4j query results with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache = {}

    def _key(self, query: str, params: dict) -> str:
        """Generate cache key from query + params."""
        param_str = ";".join(
            f"{k}={str(v)}" for k, v in sorted(params.items())
        )
        combined = f"{query}:::{param_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, query: str, params: dict) -> Optional[Any]:
        """Get cached result if exists and not expired."""
        key = self._key(query, params)
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, query: str, params: dict, result: Any):
        """Cache result with TTL."""
        key = self._key(query, params)
        expiry = time.time() + self.ttl_seconds
        self._cache[key] = (result, expiry)

    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        now = time.time()
        valid = sum(
            1 for _, (_, expiry) in self._cache.items() if now < expiry
        )
        return {
            "size": len(self._cache),
            "valid_entries": valid,
            "expired_entries": len(self._cache) - valid,
        }


# Global cache instance (1 hour TTL for governance paths)
_query_cache = QueryCache(ttl_seconds=3600)


def cached_query(func: Callable) -> Callable:
    """Decorator to cache expensive Neo4j query results.

    Wraps functions that execute Neo4j queries. Results are cached if query
    and parameters are identical.

    Usage:
        @cached_query
        def get_role_training_paths(driver, role_name):
            with driver.session() as session:
                return session.run(query, role=role_name).data()
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract query string and params from function context
        # (simplified: assumes function uses predictable param naming)
        query_str = func.__doc__ or ""  # Query in docstring
        cache_key = f"{func.__name__}:{args}:{kwargs}"

        # Check cache first (simplified key for demo)
        cached = _query_cache.get(cache_key, {})
        if cached is not None:
            return cached

        # Execute function and cache result
        result = func(*args, **kwargs)
        _query_cache.set(cache_key, {}, result)
        return result

    return wrapper


def cache_invalidate():
    """Clear all cached query results (called on seed_graph re-run)."""
    _query_cache.clear()


def cache_stats() -> dict:
    """Get cache statistics (for monitoring/debugging)."""
    return _query_cache.stats()
