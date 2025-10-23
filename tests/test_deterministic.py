import pytest
from common.fountain.encoder import LTEncoder
from decoder.reassembler import LTDecoder

def test_systematic_roundtrip():
    data = b"HELLO FOUNTAIN"
    block_size = 4
    encoder = LTEncoder(data, block_size, systematic=True)
    k = len(encoder.blocks)
    decoder = LTDecoder(block_size, k, orig_len=len(data))

    for idxs, payload in encoder.emit_systematic():
        decoder.add_symbol(idxs, payload)

    result = decoder.decode()
    assert result == data
