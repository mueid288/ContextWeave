"""Exact-prefix KV cache simulator with optional LRU token budget (Gemini_3 trap 3)."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class PrefixHit:
    matched_tokens: int
    cached: bool


@dataclass
class PrefixCacheSimulator:
    """
    Radix-style longest prefix match. Optionally capped by a token budget so
    native prefix caching is not assumed infinite-HBM on long traces.

    Budget accounting counts **unique trie nodes** (shared prefixes counted once),
    matching how a radix/prefix KV cache shares storage along common paths.
    """

    budget_tokens: int | None = None  # None = unbounded (legacy)
    _roots: dict[int, "_Node"] = field(default_factory=dict)
    # LRU of full prompt token tuples for eviction (only when budget set)
    _lru: OrderedDict[tuple[int, ...], None] = field(default_factory=OrderedDict)
    _tokens_stored: int = 0
    total_lookups: int = 0
    total_hits: int = 0
    total_matched_tokens: int = 0
    total_prompt_tokens: int = 0
    evictions: int = 0

    def lookup(self, token_ids: list[int]) -> PrefixHit:
        self.total_lookups += 1
        self.total_prompt_tokens += len(token_ids)
        matched = self._longest_prefix(token_ids)
        if matched > 0:
            self.total_hits += 1
            self.total_matched_tokens += matched
        return PrefixHit(matched_tokens=matched, cached=matched > 0)

    def insert(self, token_ids: list[int]) -> None:
        if not token_ids:
            return
        key = tuple(token_ids)
        if key in self._lru:
            self._lru.move_to_end(key)
            return
        if self.budget_tokens is not None:
            # A prompt longer than the budget can never fit (empty-cache node count
            # equals prompt length for a unique path).
            if len(token_ids) > self.budget_tokens:
                return
            while True:
                new_nodes = self._count_new_nodes(token_ids)
                if self._tokens_stored + new_nodes <= self.budget_tokens:
                    break
                if not self._lru:
                    return
                # Batch-evict until estimated freed length covers the deficit, then
                # rebuild the trie once. Loop if sharing meant we freed fewer unique nodes.
                deficit = self._tokens_stored + new_nodes - self.budget_tokens
                freed_estimate = 0
                while self._lru and freed_estimate < deficit:
                    old, _ = self._lru.popitem(last=False)
                    self.evictions += 1
                    freed_estimate += len(old)
                self._rebuild_trie()
                self._tokens_stored = self._count_trie_nodes()
        added = self._insert_into_trie(token_ids)
        self._lru[key] = None
        self._tokens_stored += added

    def _rebuild_trie(self) -> None:
        self._roots.clear()
        for prompt in self._lru:
            self._insert_into_trie(list(prompt))

    def _count_trie_nodes(self) -> int:
        # Iterative — synthetic prompts can be thousands of tokens deep.
        count = 0
        stack = list(self._roots.values())
        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children.values())
        return count

    def _count_new_nodes(self, token_ids: list[int]) -> int:
        """How many trie nodes would be created by inserting this prompt."""
        if not token_ids:
            return 0
        node = self._roots.get(token_ids[0])
        if node is None:
            return len(token_ids)
        for i, tok in enumerate(token_ids[1:], start=1):
            nxt = node.children.get(tok)
            if nxt is None:
                return len(token_ids) - i
            node = nxt
        return 0

    def _insert_into_trie(self, token_ids: list[int]) -> int:
        """Insert prompt into trie; return number of newly created nodes."""
        if not token_ids:
            return 0
        added = 0
        node = self._roots.get(token_ids[0])
        if node is None:
            node = _Node(token=token_ids[0])
            self._roots[token_ids[0]] = node
            added += 1
        for tok in token_ids[1:]:
            nxt = node.children.get(tok)
            if nxt is None:
                nxt = _Node(token=tok)
                node.children[tok] = nxt
                added += 1
            node = nxt
        node.terminal = True
        return added

    def _longest_prefix(self, token_ids: list[int]) -> int:
        if not token_ids:
            return 0
        node = self._roots.get(token_ids[0])
        if node is None:
            return 0
        matched = 1
        for tok in token_ids[1:]:
            nxt = node.children.get(tok)
            if nxt is None:
                break
            node = nxt
            matched += 1
        return matched


@dataclass
class _Node:
    token: int
    children: dict[int, "_Node"] = field(default_factory=dict)
    terminal: bool = False
