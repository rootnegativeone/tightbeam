"""
Channel simulators for fountain testing.

Includes a simple burst eraser and a Gilbert-Elliott two-state channel model.
"""

import random
from typing import Iterable, List, Sequence, Tuple


def burst_eraser(symbols: list, loss_rate: float = 0.2, burst_len: int = 5) -> list:
    """Simulate random bursts of erasures over the symbol list.

    loss_rate controls how often a burst begins; burst_len controls the
    maximum length of each burst.
    """
    n = len(symbols)
    keep = []
    i = 0
    while i < n:
        if random.random() < loss_rate:
            # drop a burst
            drop = random.randint(1, burst_len)
            i += drop
        else:
            keep.append(symbols[i])
            i += 1
    return keep


def gilbert_elliott_eraser(
    symbols: Sequence[Tuple[Iterable[int], bytes]],
    p: float = 0.05,
    r: float = 0.25,
    good_loss: float = 0.0,
    bad_loss: float = 0.8,
    start_state: str = "good",
) -> List[Tuple[Iterable[int], bytes]]:
    """Gilbert-Elliott channel eraser.

    - p: Probability to transition Good -> Bad each step
    - r: Probability to transition Bad -> Good each step
    - good_loss: Erasure probability in Good state
    - bad_loss: Erasure probability in Bad state
    - start_state: "good" or "bad"
    """
    state = 0 if start_state.lower().startswith("g") else 1  # 0=good, 1=bad
    out = []
    for sym in symbols:
        # Drop with state-dependent loss probability
        if state == 0:
            if random.random() >= good_loss:
                out.append(sym)
            # Transition
            if random.random() < p:
                state = 1
        else:
            if random.random() >= bad_loss:
                out.append(sym)
            # Transition
            if random.random() < r:
                state = 0
    return out
