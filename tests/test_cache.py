"""Redis cache behaviour - Upstash is mocked, no network. The invariant under
test: caching can only ever make things faster, never break a turn."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import fintra.memory.cache as cache
from fintra.config import get_settings

HISTORY = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]


def _enable_redis(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-token")
    get_settings.cache_clear()


def _disable_redis(monkeypatch):
    # empty-string env vars override any real values in a local .env,
    # covering every alias name the settings accept
    for name in (
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "UPSTASH_REDIS_KV_REST_API_URL",
        "UPSTASH_REDIS_KV_REST_API_TOKEN",
        "KV_REST_API_URL",
        "KV_REST_API_TOKEN",
    ):
        monkeypatch.setenv(name, "")
    get_settings.cache_clear()


def test_disabled_cache_is_a_noop(monkeypatch):
    _disable_redis(monkeypatch)
    called = MagicMock()
    monkeypatch.setattr(cache.httpx, "post", called)

    assert cache.get_history("s1") is None
    cache.set_history("s1", HISTORY)
    called.assert_not_called()


def test_cache_hit_returns_history(monkeypatch):
    _enable_redis(monkeypatch)
    response = SimpleNamespace(
        json=lambda: {"result": json.dumps(HISTORY)}, raise_for_status=lambda: None
    )
    monkeypatch.setattr(cache.httpx, "post", lambda *a, **kw: response)

    assert cache.get_history("s1") == HISTORY


def test_cache_miss_returns_none(monkeypatch):
    _enable_redis(monkeypatch)
    response = SimpleNamespace(json=lambda: {"result": None}, raise_for_status=lambda: None)
    monkeypatch.setattr(cache.httpx, "post", lambda *a, **kw: response)

    assert cache.get_history("s1") is None


def test_redis_failure_degrades_silently(monkeypatch):
    _enable_redis(monkeypatch)

    def boom(*a, **kw):
        raise ConnectionError("upstash down")

    monkeypatch.setattr(cache.httpx, "post", boom)
    assert cache.get_history("s1") is None  # miss, not crash
    cache.set_history("s1", HISTORY)  # no exception


def test_corrupt_cache_entry_is_a_miss(monkeypatch):
    _enable_redis(monkeypatch)
    response = SimpleNamespace(
        json=lambda: {"result": "not-json{{"}, raise_for_status=lambda: None
    )
    monkeypatch.setattr(cache.httpx, "post", lambda *a, **kw: response)

    assert cache.get_history("s1") is None


def test_load_history_skips_supabase_on_hit(monkeypatch):
    """The point of the cache: a hit must not touch Supabase at all."""
    import fintra.memory.history as history

    monkeypatch.setattr(
        "fintra.memory.cache.get_history", lambda sid: HISTORY
    )
    monkeypatch.setattr(
        history, "_client", lambda: (_ for _ in ()).throw(AssertionError("supabase touched"))
    )
    assert history.load_history("s1", limit=10) == HISTORY
