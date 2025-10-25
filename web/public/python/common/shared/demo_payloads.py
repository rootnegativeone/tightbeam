"""
Deterministic payload generators shared across tests and web simulations.
"""

from __future__ import annotations

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


__all__ = ["generate_pos_terminal_logs"]
