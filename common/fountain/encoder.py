"""
Fountain encoder: systematic source symbols followed by seed-scheduled repair symbols.

Which blocks a symbol combines is a pure function of (seed, esi); see
``schedule.symbol_indices``. Receivers that know the seed only need each
symbol's esi, never its index list.
"""

from __future__ import annotations

import zlib
from typing import Iterator, List, Optional, Tuple

from ..shared.metrics import FountainMetrics
from ..shared.utils import split_blocks
from .schedule import symbol_indices

Symbol = Tuple[List[int], bytes]


class LTEncoder:
    def __init__(
        self,
        data: bytes,
        block_size: int,
        systematic: bool = True,
        *,
        seed: int = 0,
        integrity_check: bool = False,
        metrics: Optional[FountainMetrics] = None,
    ):
        """
        Parameters
        ----------
        systematic:
            When True, ``encode_symbol`` starts with the k source blocks
            (esi 0..k-1) before emitting repair symbols; otherwise it starts
            at the first repair symbol (esi k).
        seed:
            32-bit session seed shared with the receiver; selects which blocks
            each repair symbol combines.
        """
        self.orig_len = len(data)
        self.block_size = block_size
        self.blocks = split_blocks(data, block_size)
        self.k = len(self.blocks)
        self.seed = seed & 0xFFFFFFFF
        self.systematic = systematic
        self.generated = 0 if systematic else self.k
        self.integrity_check = integrity_check
        self.tag_bytes = 4 if integrity_check else 0
        self.metrics = metrics
        self._block_ints = [int.from_bytes(b, byteorder="big") for b in self.blocks]

    def symbol(self, esi: int) -> Symbol:
        """Return (indices, payload) for encoding symbol id ``esi``."""
        idxs = symbol_indices(self.seed, esi, self.k)
        value = 0
        for i in idxs:
            value ^= self._block_ints[i]
        payload = self._apply_integrity(value.to_bytes(self.block_size, "big"))
        if self.metrics:
            self.metrics.record_degree(len(idxs))
        return idxs, payload

    def emit_systematic(self) -> Iterator[Symbol]:
        """Yield each original block directly in systematic mode."""
        for esi in range(self.k):
            self.generated = max(self.generated, esi + 1)
            yield self.symbol(esi)

    def encode_symbol(self) -> Symbol:
        """Emit the next symbol in esi order."""
        symbol = self.symbol(self.generated)
        self.generated += 1
        return symbol

    def encode(self, n: int) -> List[Symbol]:
        return [self.encode_symbol() for _ in range(n)]

    def _apply_integrity(self, payload: bytes) -> bytes:
        """Attach integrity checksum if enabled."""
        if not self.integrity_check:
            return payload
        checksum = zlib.crc32(payload) & 0xFFFFFFFF
        return payload + checksum.to_bytes(self.tag_bytes, byteorder="big")
