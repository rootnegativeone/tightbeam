#!/usr/bin/env python3
"""
Channel benchmark for fountain encoder/decoder.

Runs Monte Carlo trials across a parameter grid and prints success rate,
average symbols used, and decode latency.
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
from pathlib import Path

# Ensure project root import
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.fountain.encoder import LTEncoder
from common.fountain.decoder import LTDecoder
from common.fountain.sim import burst_eraser, gilbert_elliott_eraser
from common.shared.metrics import FountainMetrics


def make_payload(nbytes: int, seed: int | None = None) -> bytes:
    rnd = random.Random(seed)
    return bytes(rnd.getrandbits(8) for _ in range(nbytes))


def run_trial(
    payload_len: int,
    block_size: int,
    overhead: float,
    channel: str,
    channel_kwargs: dict,
    integrity_check: bool = True,
) -> tuple[bool, FountainMetrics]:
    payload = make_payload(payload_len, seed=random.randrange(1 << 30))
    metrics = FountainMetrics()

    enc = LTEncoder(
        data=payload,
        block_size=block_size,
        systematic=True,
        integrity_check=integrity_check,
        metrics=metrics,
    )
    k = len(enc.blocks)

    symbols = list(enc.emit_systematic())
    extra = max(0, int(overhead * k))
    if extra:
        symbols.extend(enc.encode(extra))

    if channel == "burst":
        received = burst_eraser(symbols, **channel_kwargs)
    elif channel == "ge":
        received = gilbert_elliott_eraser(symbols, **channel_kwargs)
    else:
        raise ValueError(f"Unknown channel: {channel}")

    dec = LTDecoder(
        block_size=block_size,
        k=k,
        orig_len=len(payload),
        integrity_check=integrity_check,
        metrics=metrics,
    )
    for idxs, payload_bytes in received:
        dec.add_symbol(idxs, payload_bytes)

    recovered = dec.decode()
    return (recovered == payload), metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Fountain channel benchmark")
    ap.add_argument("--payload", type=int, default=16_384, help="payload bytes")
    ap.add_argument("--block", type=int, default=32, help="block size bytes")
    ap.add_argument(
        "--overheads", type=str, default="0.0,0.1,0.2,0.3", help="comma list"
    )
    ap.add_argument("--trials", type=int, default=50, help="trials per config")
    ap.add_argument("--channel", choices=["burst", "ge"], default="ge")
    ap.add_argument("--ge", type=str, default="p=0.05,r=0.25,good=0.02,bad=0.8")
    ap.add_argument(
        "--burst", type=str, default="loss=0.2,burst=3", help="loss and burst len"
    )
    args = ap.parse_args()

    overheads = [float(x) for x in args.overheads.split(",")]

    if args.channel == "ge":
        kv = dict(x.split("=") for x in args.ge.split(","))
        channel_kwargs = dict(
            p=float(kv.get("p", 0.05)),
            r=float(kv.get("r", 0.25)),
            good_loss=float(kv.get("good", 0.02)),
            bad_loss=float(kv.get("bad", 0.8)),
        )
    else:
        kv = dict(x.split("=") for x in args.burst.split(","))
        channel_kwargs = dict(
            loss_rate=float(kv.get("loss", 0.2)),
            burst_len=int(kv.get("burst", 3)),
        )

    print(
        f"Payload={args.payload}B block={args.block} channel={args.channel} params={channel_kwargs} trials={args.trials}"
    )
    for oh in overheads:
        successes = 0
        all_metrics: list[FountainMetrics] = []
        for _ in range(args.trials):
            ok, m = run_trial(
                payload_len=args.payload,
                block_size=args.block,
                overhead=oh,
                channel=args.channel,
                channel_kwargs=channel_kwargs,
                integrity_check=True,
            )
            successes += 1 if ok else 0
            all_metrics.append(m)

        # Aggregate
        merged = FountainMetrics()
        for m in all_metrics:
            merged.merge(m)
        summary = merged.summary()
        rate = successes / args.trials
        avg_used = summary.get("average_symbols_used", 0.0)
        avg_latency_ms = summary.get("average_decode_duration", 0.0) * 1000.0
        print(
            f"overhead={oh:.2f} -> success={rate * 100:5.1f}% used≈{avg_used:.1f} lat≈{avg_latency_ms:.2f}ms avg_degree={summary['average_degree']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
