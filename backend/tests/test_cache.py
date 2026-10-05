from app.cache import TTLCache


def test_entries_expire_after_ttl():
    now = [0.0]
    c = TTLCache(ttl_seconds=10, clock=lambda: now[0])
    c.set("a", 1)
    assert c.get("a") == 1
    now[0] = 9.9
    assert c.get("a") == 1
    now[0] = 10.0
    assert c.get("a") is None


def test_cache_never_grows_past_max_items():
    c = TTLCache(ttl_seconds=100, max_items=3)
    for i in range(10):
        c.set(i, i)
    assert len(c._data) <= 3
