"""
Measure how many frames the receiver needs to reach full rank with the
seed-derived repair schedule, versus the ideal 1 / (1 - loss).

Usage: python scripts/bench_schedule.py [--ks 50,107,500,2000] [--trials 10]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.fountain.decoder import LTDecoder  # noqa: E402
from common.fountain.schedule import symbol_indices  # noqa: E402


def frames_to_full_rank(k: int, loss: float, trial: int) -> float:
    rng = random.Random(trial)
    decoder = LTDecoder(block_size=8, k=k, orig_len=8 * k)
    esi = sent = 0
    while not decoder.is_complete and sent < 20 * k + 50:
        indices = symbol_indices(trial + 1, esi, k)
        esi += 1
        sent += 1
        if rng.random() >= loss:
            decoder.add_symbol(indices, bytes(8))
    return sent / k


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ks", default="8,50,107,500,2000")
    ap.add_argument("--losses", default="0.15,0.30")
    ap.add_argument("--trials", type=int, default=10)
    args = ap.parse_args()

    for k in (int(x) for x in args.ks.split(",")):
        for loss in (float(x) for x in args.losses.split(",")):
            ratios = [frames_to_full_rank(k, loss, t) for t in range(args.trials)]
            print(
                f"k={k:5} loss={loss:.0%} ideal={1 / (1 - loss):.3f} "
                f"mean={sum(ratios) / len(ratios):.3f} worst={max(ratios):.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
