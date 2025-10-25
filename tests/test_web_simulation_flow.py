"""
Web simulation flow test ensuring send/receive path survives burst losses.

This test mirrors the planned browser-based demo by taking a sample POS/IoT
log payload through the LT fountain encoder, simulating QR frame bursts, and
verifying that the decoder reconstructs the original content even after
concentrated frame drops. It gives confidence that the web UI can rely on the
core pipeline before wiring it into canvas/webcam plumbing.
"""

import random

from common.fountain.encoder import LTEncoder
from common.fountain.decoder import LTDecoder
from common.shared.demo_payloads import generate_pos_terminal_logs
from common.shared.metrics import FountainMetrics


def _simulate_burst_channel(symbols, bursts):
    """
    Drop contiguous windows of symbols, modelling a Gilbert-Elliott burst.

    Parameters
    ----------
    symbols:
        Iterable of (indices, payload) pairs from the encoder.
    bursts:
        Iterable of (start, length) tuples. Positions refer to symbol order.
    """
    drop_ranges = []
    for start, length in bursts:
        drop_ranges.append(range(start, start + length))

    delivered = []
    for idx, symbol in enumerate(symbols):
        if any(idx in drop_range for drop_range in drop_ranges):
            continue
        delivered.append(symbol)
    return delivered


def test_web_simulation_end_to_end():
    """Ensure Send → Encode → Receive → Decode survives burst loss."""
    random.seed(1337)

    payload = generate_pos_terminal_logs()
    block_size = 48
    metrics = FountainMetrics()

    encoder = LTEncoder(
        data=payload,
        block_size=block_size,
        systematic=True,
        integrity_check=True,
        metrics=metrics,
    )

    systematic_symbols = list(encoder.emit_systematic())
    redundant_symbols = encoder.encode(len(encoder.blocks) + 4)
    all_symbols = systematic_symbols + redundant_symbols

    # Simulate two burst drops totalling ~20% of the QR stream.
    bursts = [(2, 3), (9, 4)]
    delivered_symbols = _simulate_burst_channel(all_symbols, bursts)
    assert len(delivered_symbols) < len(all_symbols)

    decoder = LTDecoder(
        block_size=block_size,
        k=len(encoder.blocks),
        orig_len=len(payload),
        integrity_check=True,
        metrics=metrics,
    )

    for idxs, payload_chunk in delivered_symbols:
        decoder.add_symbol(idxs, payload_chunk)

    recovered = decoder.decode()
    assert recovered is not None
    assert recovered == payload
    byte_accuracy = sum(
        1 for src, dst in zip(recovered, payload, strict=False) if src == dst
    ) / len(payload)
    assert byte_accuracy >= 0.95

    summary = metrics.summary()
    assert summary["decode_attempts"] == 1
    assert summary["decode_success_rate"] == 1.0
    assert summary["total_symbols"] == len(all_symbols)
    assert summary["average_symbols_used"] <= len(delivered_symbols)
    delivered_fraction = len(delivered_symbols) / len(all_symbols)
    assert delivered_fraction >= 0.75
