"""
LT-style fountain decoder using incremental Gaussian elimination over GF(2).

Each symbol's index set is held as an integer bitmask and its payload as a
single big integer, so one XOR applies a row operation to every bit plane at
once. Symbols are reduced against existing pivots on arrival, which keeps the
rank exact at all times and makes the final solve a cheap back-substitution.
"""

from __future__ import annotations

import zlib
from time import perf_counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..shared.metrics import FountainMetrics
from ..shared.utils import combine_blocks


class LTDecoder:
    """Recover source blocks from LT fountain symbols."""

    def __init__(
        self,
        block_size: int,
        k: int,
        orig_len: int,
        *,
        integrity_check: bool = False,
        metrics: Optional[FountainMetrics] = None,
    ):
        """
        Parameters
        ----------
        block_size:
            Size in bytes for each original source block.
        k:
            Number of source blocks expected from the encoder.
        orig_len:
            Length of the original payload in bytes (used to trim padding).
        integrity_check:
            When True, expect a 4-byte CRC32 tag appended to each payload.
        metrics:
            Optional FountainMetrics collector for instrumentation.
        """
        self.block_size = block_size
        self.k = k
        self.orig_len = orig_len
        self.integrity_check = integrity_check
        self.tag_bytes = 4 if integrity_check else 0
        self.metrics = metrics
        # pivot column -> (row bitmask, payload int); the lowest set bit of
        # each row mask is its pivot column.
        self._pivots: Dict[int, Tuple[int, int]] = {}
        self.symbols_received = 0
        self.redundant_symbols = 0
        self._result: Optional[bytes] = None
        # Column pinned down by the most recent symbol, or None if it added no
        # rank. Repair symbols always pivot on a column no earlier symbol
        # covered, so this shows which "gap" a symbol filled.
        self.last_pivot_col: Optional[int] = None
        self.last_pivots = 0
        self.last_rank = 0

    @property
    def rank(self) -> int:
        """Number of linearly independent symbols collected so far."""
        return len(self._pivots)

    @property
    def is_complete(self) -> bool:
        return len(self._pivots) == self.k

    def add_symbol(self, idxs: int | Iterable[int], payload: bytes) -> bool:
        """
        Add a received symbol, dropping it if integrity checks fail.

        Returns True when the symbol passed integrity checks (whether or not it
        increased the rank).
        """
        idx_list = [idxs] if isinstance(idxs, int) else list(idxs)

        payload_bytes = payload
        if self.tag_bytes:
            if len(payload_bytes) < self.tag_bytes:
                if self.metrics:
                    self.metrics.record_symbol_rejected("too_short")
                return False
            data = payload_bytes[: -self.tag_bytes]
            provided = payload_bytes[-self.tag_bytes :]
            expected = zlib.crc32(data) & 0xFFFFFFFF
            if provided != expected.to_bytes(self.tag_bytes, byteorder="big"):
                if self.metrics:
                    self.metrics.record_symbol_rejected("crc_mismatch")
                return False
            payload_bytes = data

        self.symbols_received += 1
        self.last_pivot_col = self._reduce_and_insert(idx_list, payload_bytes)
        if self.last_pivot_col is None:
            self.redundant_symbols += 1
        self.last_rank = self.last_pivots = len(self._pivots)
        return True

    def _reduce_and_insert(
        self, idx_list: Sequence[int], payload: bytes
    ) -> Optional[int]:
        """Reduce a symbol against existing pivots; return its new pivot column."""
        if self.is_complete:
            return None

        mask = 0
        for i in idx_list:
            if not 0 <= i < self.k:
                raise ValueError(f"symbol index {i} outside range 0..{self.k - 1}")
            mask ^= 1 << i
        value = int.from_bytes(payload, byteorder="big")

        pivots = self._pivots
        while mask:
            col = (mask & -mask).bit_length() - 1
            pivot = pivots.get(col)
            if pivot is None:
                pivots[col] = (mask, value)
                return col
            mask ^= pivot[0]
            value ^= pivot[1]
        return None

    def decode(self) -> bytes | None:
        """
        Attempt to reconstruct the original payload.

        Returns the recovered bytes or ``None`` if the system is underdetermined.
        """
        if self._result is not None:
            return self._result

        if self.symbols_received < self.k:
            return None

        start = perf_counter()
        rank = len(self._pivots)
        if rank < self.k:
            if self.metrics:
                self.metrics.record_decode(
                    perf_counter() - start, False, rank, self.symbols_received
                )
            return None

        # Every pivot row only has bits at or above its pivot column, so solving
        # from the highest column down needs each referenced block already known.
        solution = [0] * self.k
        for col in range(self.k - 1, -1, -1):
            mask, value = self._pivots[col]
            mask ^= 1 << col
            while mask:
                low = mask & -mask
                value ^= solution[low.bit_length() - 1]
                mask ^= low
            solution[col] = value

        blocks = self._convert_ints_to_blocks(solution)
        self._result = combine_blocks(blocks, self.orig_len)
        if self.metrics:
            self.metrics.record_decode(
                perf_counter() - start, True, self.k, self.symbols_received
            )
        return self._result

    def _convert_ints_to_blocks(self, values: Sequence[int]) -> List[bytes]:
        """Convert integer block representations back to fixed-size byte blocks."""
        return [value.to_bytes(self.block_size, byteorder="big") for value in values]


__all__ = ["LTDecoder"]
