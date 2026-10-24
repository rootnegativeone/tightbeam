"""
Deterministic payload generators shared across tests and web simulations.
"""

from __future__ import annotations

import json
import random
from typing import Iterable, Mapping, Sequence


def _format_log_entry(entry: Mapping[str, object]) -> str:
    """Render a single log entry as pipe-delimited key=value pairs."""
    return "|".join(f"{key}={value}" for key, value in entry.items())


def generate_pos_terminal_logs(
    additional_entries: Iterable[Mapping[str, object]] | None = None,
) -> bytes:
    """
    Return synthetic POS/IoT style logs used by the web demo and tests.

    Parameters
    ----------
    additional_entries:
        Optional iterable of extra log dictionaries appended to the default set.
    """

    default_entries: Sequence[Mapping[str, object]] = (
        {
            "terminal": "TB-POS-01",
            "event": "sale_approved",
            "amount": "23.75",
            "currency": "USD",
            "method": "tap",
            "latency_ms": 412,
        },
        {
            "terminal": "TB-POS-01",
            "event": "inventory_sync",
            "status": "ok",
            "duration_ms": 128,
        },
        {
            "gateway": "tightbeam-edge",
            "event": "burst_monitor",
            "window": "60s",
            "drops_detected": 0,
        },
        {
            "terminal": "TB-POS-02",
            "event": "sale_declined",
            "amount": "109.99",
            "currency": "USD",
            "method": "chip",
            "reason": "issuer_declined",
        },
        {
            "gateway": "tightbeam-edge",
            "event": "latency_sample",
            "p95_ms": 537,
            "p99_ms": 804,
        },
        {
            "terminal": "TB-POS-03",
            "event": "firmware_status",
            "version": "2.4.7",
            "uptime_hours": 132,
            "battery_percent": 88,
        },
    )

    entries: list[Mapping[str, object]] = list(default_entries)
    if additional_entries:
        entries.extend(additional_entries)

    header = {
        "log_format": "json_lines",
        "source": "tightbeam_web_demo",
        "total_entries": len(entries),
    }

    lines = [_format_log_entry(header)]
    lines.extend(_format_log_entry(entry) for entry in entries)
    return "\n".join(lines).encode("utf-8")


_BULK_EVENTS = (
    "sale_approved",
    "sale_declined",
    "card_read",
    "inventory_sync",
    "heartbeat",
    "printer_status",
    "settlement_batch",
)


def generate_bulk_pos_logs(target_bytes: int, seed: int = 1337) -> bytes:
    """
    Return deterministic JSON-lines POS logs of roughly ``target_bytes``.

    Includes high-entropy fields (transaction ids, amounts, latencies) so the
    compression ratio resembles a real merchant log pull (~8x with deflate)
    rather than a trivially repetitive payload.
    """
    rng = random.Random(seed)
    lines: list[str] = []
    size = 0
    ts = 1_729_600_000
    while size < target_bytes:
        ts += rng.randint(1, 40)
        line = json.dumps(
            {
                "ts": ts,
                "terminal": f"TB-POS-{rng.randint(1, 4):02d}",
                "event": rng.choice(_BULK_EVENTS),
                "txn_id": f"{rng.getrandbits(64):016x}",
                "amount": f"{rng.uniform(1, 200):.2f}",
                "currency": "USD",
                "method": rng.choice(("tap", "chip", "swipe")),
                "latency_ms": rng.randint(80, 900),
                "fw": "4.2.17",
            },
            separators=(",", ":"),
        )
        lines.append(line)
        size += len(line) + 1
    return "\n".join(lines).encode("utf-8")[:target_bytes]


__all__ = ["generate_bulk_pos_logs", "generate_pos_terminal_logs"]
