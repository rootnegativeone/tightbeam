"""
Deterministic mapping from (seed, esi) to the source blocks a symbol combines.

Encoder and receiver both derive a symbol's index set from the session seed and
its encoding symbol id (esi), so frames never carry index lists. Everything here
is integer-only (splitmix64 + modulo) so a non-Python encoder can reproduce it
bit for bit.

- esi < k: systematic symbol, indices [esi].
- esi >= k: repair symbol of degree ``repair_degree(k)`` or one less (chosen
  by the first PRNG output, so rows of both parities exist; a single fixed
  even degree would leave every repair row in the even-weight subspace and cap
  rank at k-1). Indices are drawn without replacement from splitmix64 seeded by
  (seed, esi).
"""

from __future__ import annotations

from typing import List, Tuple

_MASK64 = (1 << 64) - 1


def _splitmix64(state: int) -> Tuple[int, int]:
    """Advance a splitmix64 state; return (next_state, output)."""
    state = (state + 0x9E3779B97F4A7C15) & _MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    return state, z ^ (z >> 31)


def repair_degree(k: int) -> int:
    """
    Maximum number of source blocks combined into a repair symbol.

    Grows with log2(k) so a handful of repair symbols can cover any lost
    systematic block; capped near k/2 because denser rows stop adding rank
    (degree k makes every repair symbol identical). With systematic symbols at
    15-30% loss, full rank arrives within ~4% of the ideal 1/(1-loss) frames
    for k = 50..5000 (see docs/wire_format_v2.md).
    """
    if k <= 1:
        return 1
    return min(4 * k.bit_length() + 4, max(2, (k + 1) // 2))


def symbol_indices(seed: int, esi: int, k: int) -> List[int]:
    """Return the sorted source-block indices combined into symbol ``esi``."""
    if k <= 0:
        return []
    if esi < k:
        return [esi]

    state = ((seed & 0xFFFFFFFF) << 32) | (esi & 0xFFFFFFFF)
    state, value = _splitmix64(state)
    degree = max(1, repair_degree(k) - (value & 1))
    chosen: set[int] = set()
    while len(chosen) < degree:
        state, value = _splitmix64(state)
        chosen.add(value % k)
    return sorted(chosen)


__all__ = ["repair_degree", "symbol_indices"]
