"""
Deterministic POS/IoT style logs used by the web simulation.
"""


def generate_sample_logs() -> bytes:
    """Return demo logs that feel like a payment terminal event stream."""
    entries = [
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
    ]

    header = {
        "log_format": "json_lines",
        "source": "tightbeam_web_demo",
        "total_entries": len(entries),
    }

    lines = ["|".join(f"{k}={v}" for k, v in header.items())]
    for entry in entries:
        lines.append("|".join(f"{k}={v}" for k, v in entry.items()))
    return "\n".join(lines).encode("utf-8")
