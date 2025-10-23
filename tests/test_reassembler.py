# File: tests/test_reassembler.py

import pytest
from decoder.reassembler import LTDecoder
from common.fountain.encoder import LTEncoder
from common.shared.metrics import FountainMetrics


def test_basic_recovery():
    # Parameters
    orig_data = b"Hello world! Hello world! Hello world! Hello world! Hello world! Hello world! Hello world!"
    block_size = 4
    k = (len(orig_data) + block_size - 1) // block_size

    # Encode
    encoder = LTEncoder(block_size=block_size, data=orig_data)
    symbols = [encoder.encode_symbol() for _ in range(k + 5)]

    # Decode
    decoder = LTDecoder(block_size=block_size, k=k, orig_len=len(orig_data))
    for idxs, payload in symbols:
        decoder.add_symbol(idxs, payload)

    result = decoder.decode()
    assert result == orig_data


def test_decoder_ignores_degenerate_symbols():
    orig_data = b"Subset selection saves the day!"
    block_size = 4
    encoder = LTEncoder(data=orig_data, block_size=block_size, systematic=True)
    k = len(encoder.blocks)

    decoder = LTDecoder(block_size=block_size, k=k, orig_len=len(orig_data))
    decoder.add_symbol([], b"\x00" * block_size)  # Zero row should be ignored

    for idxs, payload in encoder.emit_systematic():
        decoder.add_symbol(idxs, payload)

    assert decoder.decode() == orig_data


def test_decoder_rejects_corrupted_symbol_with_crc():
    payload = b"CRC protected fountain blocks"
    block_size = 4
    metrics = FountainMetrics()
    encoder = LTEncoder(
        data=payload,
        block_size=block_size,
        systematic=True,
        integrity_check=True,
        metrics=metrics,
    )
    symbols = list(encoder.emit_systematic())
    k = len(encoder.blocks)

    decoder = LTDecoder(
        block_size=block_size,
        k=k,
        orig_len=len(payload),
        integrity_check=True,
        metrics=metrics,
    )

    idxs, payload_bytes = symbols[0]
    corrupted = bytearray(payload_bytes)
    corrupted[0] ^= 0xFF
    decoder.add_symbol(idxs, bytes(corrupted))  # Should be rejected by CRC check

    for idxs, payload_bytes in symbols:
        decoder.add_symbol(idxs, payload_bytes)

    result = decoder.decode()
    assert result == payload
    assert metrics.rejected_symbols.get("crc_mismatch", 0) == 1
