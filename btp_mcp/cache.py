"""
cache.py — A simple TTL (time-to-live) cache for BTP API responses.

NEW in Phase 2. This file didn't exist in Phase 1.

Why do we need caching?
  BTP API calls take ~200-500ms each.
  If Claude asks "what services do I have?" and we call BTP every single time,
  it feels slow — especially when the data barely changes.

  BTP service catalog, entitlements, and destinations change rarely
  (hours to days). Caching them for 5 minutes means:
    - Fast responses for repeated questions
    - Fewer BTP API calls (important in trial accounts with rate limits)
    - Same data quality (stale by at most 5 minutes)

How TTLCache works:
  - It's a dictionary that automatically expires entries after N seconds
  - We use the function name as the cache key
  - First call: fetches from BTP, stores in cache, returns result
  - Subsequent calls within TTL: returns cached result immediately
  - After TTL expires: fetches fresh data from BTP again

Example with CACHE_TTL_SECONDS=300 (5 minutes):
  10:00:00 → first call → fetches from BTP → caches
  10:02:00 → second call → returns cached result (fast!)
  10:07:00 → third call → TTL expired → fetches from BTP again
"""

from cachetools import TTLCache
from config import settings


# One shared cache for the whole application.
# maxsize=50 means we can cache up to 50 different keys.
# We have ~5 different API calls, so this is plenty.
# ttl comes from settings (default: 300 seconds = 5 minutes)
_cache: TTLCache = TTLCache(
    maxsize=50,
    ttl=settings.cache_ttl_seconds,
)


def get_cached(key: str):
    """
    Returns the cached value for this key, or None if not cached.

    Usage:
        result = get_cached("service_offerings")
        if result is not None:
            return result   # cache hit — return immediately
        # cache miss — go fetch from BTP
    """
    return _cache.get(key)


def set_cached(key: str, value) -> None:
    """
    Stores a value in the cache under the given key.
    It will automatically expire after settings.cache_ttl_seconds seconds.

    Usage:
        set_cached("service_offerings", my_list_of_services)
    """
    _cache[key] = value


def clear_cache() -> None:
    """
    Empties the entire cache.
    Useful in tests — ensures each test starts with a clean slate.
    Also useful if you want to force a fresh fetch during development.
    """
    _cache.clear()


def cache_info() -> dict:
    """
    Returns current cache statistics.
    Helpful for debugging — shows what's cached and the TTL setting.
    """
    return {
        "entries_cached": len(_cache),
        "max_size": _cache.maxsize,
        "ttl_seconds": _cache.ttl,
        "cached_keys": list(_cache.keys()),
    }