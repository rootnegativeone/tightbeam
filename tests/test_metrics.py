from common.fountain.encoder import LTEncoder
from common.fountain.decoder import LTDecoder
from common.shared.metrics import FountainMetrics


def test_metrics_summary_tracks_degrees_and_decode_success():
    data = b"metrics-matter" * 2
    block_size = 4
    metrics = FountainMetrics()

    encoder = LTEncoder(
        data=data,
        block_size=block_size,
        systematic=True,
        integrity_check=True,
        metrics=metrics,
    )

    systematic = list(encoder.emit_systematic())
    redundant = encoder.encode(len(encoder.blocks))
    symbols = systematic + redundant

    decoder = LTDecoder(
        block_size=block_size,
        k=len(encoder.blocks),
        orig_len=len(data),
        integrity_check=True,
        metrics=metrics,
    )

    for idxs, payload in symbols:
        decoder.add_symbol(idxs, payload)

    recovered = decoder.decode()

    assert recovered == data
    assert metrics.decode_attempts == 1
    assert metrics.decode_successes == 1
    assert metrics.degree_hist[1] >= len(encoder.blocks)

    summary = metrics.summary()
    assert summary["total_symbols"] == len(symbols)
    assert summary["decode_attempts"] == 1
    assert summary["decode_success_rate"] == 1.0
    assert summary["average_degree"] >= 1.0
