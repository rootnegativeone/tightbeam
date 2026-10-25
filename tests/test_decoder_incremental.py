"""
Rank tracking and scaling checks for the incremental LT decoder.
"""

import random
from time import perf_counter

from common.fountain.decoder import LTDecoder
from common.fountain.encoder import LTEncoder


def _random_payload(rng: random.Random, size: int) -> bytes:
    return bytes(rng.getrandbits(8) for _ in range(size))


def test_rank_ignores_duplicate_and_dependent_symbols():
    rng = random.Random(7)
    payload = _random_payload(rng, 4 * 16)
    encoder = LTEncoder(payload, 16, systematic=True, rng=rng)
    blocks = encoder.blocks
    decoder = LTDecoder(16, encoder.k, len(payload))

    assert decoder.add_symbol([0], blocks[0])
    assert decoder.rank == 1
    assert decoder.add_symbol([0], blocks[0])  # duplicate
    assert decoder.rank == 1

    combo = bytes(a ^ b for a, b in zip(blocks[0], blocks[1]))
    assert decoder.add_symbol([0, 1], combo)
    assert decoder.rank == 2
    assert decoder.add_symbol([1], blocks[1])  # dependent on rows 0 and 0^1
    assert decoder.rank == 2
    assert decoder.redundant_symbols == 2

    assert decoder.add_symbol([2], blocks[2])
    assert decoder.decode() is None  # rank 3 < k

    assert decoder.add_symbol(
        [1, 3], bytes(a ^ b for a, b in zip(blocks[1], blocks[3]))
    )
    assert decoder.is_complete
    assert decoder.decode() == payload


def test_rank_is_monotonic_and_reaches_k():
    rng = random.Random(11)
    payload = _random_payload(rng, 3000)
    encoder = LTEncoder(payload, 32, systematic=False, rng=rng)
    decoder = LTDecoder(32, encoder.k, len(payload))

    last_rank = 0
    for _ in range(encoder.k * 4):
        decoder.add_symbol(*encoder.encode_symbol())
        assert decoder.rank >= last_rank
        last_rank = decoder.rank
        if decoder.is_complete:
            break

    assert decoder.decode() == payload


def test_large_payload_decodes_quickly_under_loss():
    rng = random.Random(1337)
    payload = _random_payload(rng, 100 * 1024)
    encoder = LTEncoder(payload, 96, systematic=True, integrity_check=True, rng=rng)
    symbols = list(encoder.emit_systematic()) + encoder.encode(encoder.k)
    received = [s for s in symbols if rng.random() > 0.15]

    decoder = LTDecoder(96, encoder.k, len(payload), integrity_check=True)
    start = perf_counter()
    for idxs, data in received:
        decoder.add_symbol(idxs, data)
    result = decoder.decode()
    elapsed = perf_counter() - start

    assert result == payload
    assert elapsed < 1.0
