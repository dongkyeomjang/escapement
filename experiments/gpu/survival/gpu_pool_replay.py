"""Block-exact replay of vLLM 0.22.0's KV block pool for sequential requests.

GPU wrapper for GTASK04 (directive G-02 5.1): the semantics that
``src/continuum/model/`` does not carry are implemented here, from the
source-read in GTASK01 and the Stage 0 facts in GTASK02, and nowhere else:

* one null block (block 0) is never handed out            block_pool.py:176
* free queue starts in block-id order; never-used blocks
  are therefore consumed before any released block        kv_cache_utils.py:173
* allocation pops from the head; a popped block that
  carries a hash is evicted from the cache                block_pool.py:347,365
* a finished request's blocks are appended to the tail
  in reverse order (tail block first)                     single_type_kv_cache_manager.py:350
* lookup precedes allocation; hit blocks are touched
  (removed from the queue) before new blocks are popped   scheduler.py:594->721, kv_cache_manager.py:397,404
* hit = longest chain of cached full blocks within
  num_tokens - 1                                           kv_cache_manager.py:219
* every KV-computed token is cacheable, generated ones
  included; the last sampled token is never computed     request.py:232; GTASK02 H5
* prefill is chunked by the per-step token budget

Only sequential use is modelled (one request at a time), which is the
GTASK04 protocol. It is a replay of the rules above, not of vLLM's code.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class Block:
    bid: int
    key: tuple | None = None   # prefix tuple up to this block's end (the hash)
    ref: int = 0


@dataclass
class RequestResult:
    hit_tokens: int
    blocks_allocated: int
    evicted_keys: list = field(default_factory=list)


class GpuPoolReplay:
    def __init__(self, num_gpu_blocks: int, block_size: int = 16, budget: int = 2048):
        self.bs = block_size
        self.budget = budget
        self.blocks = [Block(i) for i in range(num_gpu_blocks)]
        # OrderedDict as an O(1) removable queue: head = next to allocate.
        self.free: "OrderedDict[int, None]" = OrderedDict((i, None) for i in range(1, num_gpu_blocks))
        self.cache: dict[tuple, int] = {}
        self.evictions: list[tuple] = []   # keys in eviction order

    # -- pool primitives -----------------------------------------------------
    def _pop(self) -> Block:
        bid, _ = self.free.popitem(last=False)
        b = self.blocks[bid]
        if b.key is not None:
            if self.cache.get(b.key) == bid:
                del self.cache[b.key]
                self.evictions.append(b.key)
            b.key = None
        assert b.ref == 0
        b.ref = 1
        return b

    def _touch(self, b: Block) -> None:
        if b.ref == 0:
            del self.free[b.bid]
        b.ref += 1

    def _free(self, req_blocks: list[Block]) -> None:
        for b in reversed(req_blocks):
            b.ref -= 1
            if b.ref == 0:
                self.free[b.bid] = None

    def lookup(self, tokens: list) -> list[Block]:
        limit = (len(tokens) - 1) // self.bs
        hit = []
        for i in range(limit):
            key = tuple(tokens[: (i + 1) * self.bs])
            bid = self.cache.get(key)
            if bid is None:
                break
            hit.append(self.blocks[bid])
        return hit

    # -- one request, run to completion ------------------------------------
    def run(self, prompt: list, generated: list) -> RequestResult:
        """``generated`` holds every output token; all but the last are fed back."""
        n_before = len(self.evictions)
        hit = self.lookup(prompt)
        for b in hit:
            self._touch(b)
        blocks = list(hit)
        computed = len(hit) * self.bs
        fed = list(prompt) + list(generated[:-1])
        allocated = 0

        def ensure(n_tokens: int) -> None:
            nonlocal allocated
            need = -(-n_tokens // self.bs)
            while len(blocks) < need:
                blocks.append(self._pop())
                allocated += 1

        def cache_full(upto: int) -> None:
            for i in range(upto // self.bs):
                b = blocks[i]
                if b.key is None:
                    key = tuple(fed[: (i + 1) * self.bs])
                    if key not in self.cache:
                        self.cache[key] = b.bid
                        b.key = key
                    else:
                        b.key = None   # duplicate content; vLLM keeps the first mapping

        # prefill, chunked by the budget
        while computed < len(prompt):
            chunk = min(self.budget, len(prompt) - computed)
            ensure(computed + chunk)
            computed += chunk
            cache_full(computed)
        # decode: each generated token except the last is fed once
        while computed < len(fed):
            ensure(computed + 1)
            computed += 1
            cache_full(computed)
        self._free(blocks)
        return RequestResult(hit_tokens=len(hit) * self.bs, blocks_allocated=allocated,
                             evicted_keys=self.evictions[n_before:])
