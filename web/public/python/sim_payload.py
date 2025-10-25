"""
Deterministic POS/IoT style logs used by the web simulation.
"""

from common.shared.demo_payloads import generate_pos_terminal_logs


def generate_sample_logs() -> bytes:
    """Return demo logs that feel like a payment terminal event stream."""
    return generate_pos_terminal_logs()
