from contextweave.trace_analysis.prefix_cache import PrefixCacheSimulator


def test_exact_prefix_hit_grows_with_shared_prefix():
    cache = PrefixCacheSimulator()
    prompt_a = [1, 2, 3, 4, 5]
    cache.insert(prompt_a)

    hit = cache.lookup([1, 2, 3, 9, 9])
    assert hit.matched_tokens == 3
    assert hit.cached


def test_miss_on_disjoint_prompt():
    cache = PrefixCacheSimulator()
    cache.insert([1, 2, 3])
    hit = cache.lookup([9, 8, 7])
    assert hit.matched_tokens == 0
    assert not hit.cached


def test_oversized_prompt_rejected_without_eviction():
    cache = PrefixCacheSimulator(budget_tokens=100)
    prompt_50 = list(range(50))
    cache.insert(prompt_50)

    prompt_200 = list(range(1000, 1200))
    cache.insert(prompt_200)

    hit_200 = cache.lookup(prompt_200)
    assert hit_200.matched_tokens == 0
    assert not hit_200.cached

    hit_50 = cache.lookup(prompt_50)
    assert hit_50.matched_tokens == 50
    assert hit_50.cached

    assert cache.evictions == 0


def test_lru_eviction_under_budget():
    cache = PrefixCacheSimulator(budget_tokens=100)
    prompt_a = list(range(100, 160))
    prompt_b = list(range(200, 260))

    cache.insert(prompt_a)
    cache.insert(prompt_b)

    hit_a = cache.lookup(prompt_a)
    assert hit_a.matched_tokens == 0
    assert not hit_a.cached

    hit_b = cache.lookup(prompt_b)
    assert hit_b.matched_tokens == 60
    assert hit_b.cached

    assert cache.evictions >= 1


def test_trie_rebuild_once_per_insert(monkeypatch):
    cache = PrefixCacheSimulator(budget_tokens=100)
    p1 = list(range(10, 30))  # 20 tokens
    p2 = list(range(30, 50))  # 20 tokens
    p3 = list(range(50, 70))  # 20 tokens
    p4 = list(range(70, 90))  # 20 tokens
    cache.insert(p1)
    cache.insert(p2)
    cache.insert(p3)
    cache.insert(p4)

    # Inserting p5 (50 tokens) exceeds remaining budget (stored: 80, 80 + 50 = 130 > 100).
    # Evicts p1 then p2 until unique-node count fits; may rebuild once per eviction.
    p5 = list(range(100, 150))

    rebuild_calls = 0
    orig_rebuild = cache._rebuild_trie

    def counting_rebuild():
        nonlocal rebuild_calls
        rebuild_calls += 1
        return orig_rebuild()

    monkeypatch.setattr(cache, "_rebuild_trie", counting_rebuild)
    cache.insert(p5)

    # Batched eviction rebuilds the trie once per insert when estimates suffice.
    assert rebuild_calls == 1
    assert cache.evictions == 2
    # p1 and p2 must be evicted
    assert cache.lookup(p1).matched_tokens == 0
    assert cache.lookup(p2).matched_tokens == 0
    # p3, p4, and p5 must remain matched
    assert cache.lookup(p3).matched_tokens == 20
    assert cache.lookup(p4).matched_tokens == 20
    assert cache.lookup(p5).matched_tokens == 50


def test_shared_prefix_counted_once_in_budget():
    """Shared radix paths must not inflate _tokens_stored (unique nodes only)."""
    cache = PrefixCacheSimulator(budget_tokens=100)
    base = list(range(80))
    a = base + [100]
    b = base + [200]
    cache.insert(a)
    assert cache._tokens_stored == 81
    cache.insert(b)
    # Only one new leaf node; no eviction despite 81+81 naive sum.
    assert cache.evictions == 0
    assert cache._tokens_stored == 82
    assert cache.lookup(a).matched_tokens == 81
    assert cache.lookup(b).matched_tokens == 81
