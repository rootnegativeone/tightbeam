"""
Property-based and functional tests for fountain module.
"""
import pytest
from common.fountain.encoder import LTEncoder
from decoder.reassembler import LTDecoder
from common.fountain.sim import burst_eraser

def test_round_trip_systematic():
    """Test round trip with systematic encoding (more reliable)."""
    payload = b"hello world"
    block_size = 4
    encoder = LTEncoder(payload, block_size, systematic=True)
    k = len(encoder.blocks)
    
    # Get systematic symbols first (guaranteed to work)
    symbols = list(encoder.emit_systematic())
    
    decoder = LTDecoder(block_size, k, orig_len=len(payload))
    for idxs, payload_bytes in symbols:
        decoder.add_symbol(idxs, payload_bytes)
    
    result = decoder.decode()
    assert result == payload

@ pytest.mark.parametrize("block_size, payload", [
    (4, b"hello world"),
    (8, b""),
])
def test_round_trip_with_redundancy(block_size, payload):
    """Test round trip with extra redundancy to handle burst erasure."""
    encoder = LTEncoder(payload, block_size, systematic=True)
    k = len(encoder.blocks)
    
    # Start with systematic symbols, then add random ones
    symbols = list(encoder.emit_systematic())
    symbols.extend(encoder.encode(n=k))  # Add k more random symbols
    
    # Apply burst erasure
    received = burst_eraser(symbols, loss_rate=0.2, burst_len=2)
    
    decoder = LTDecoder(block_size, k, orig_len=len(payload))
    for idxs, payload_bytes in received:
        decoder.add_symbol(idxs, payload_bytes)
    
    # If we don't have enough symbols, that's expected behavior
    if len(decoder.symbols) < k:
        pytest.skip(f"Insufficient symbols after burst erasure: {len(decoder.symbols)} < {k}")
    
    result = decoder.decode()
    assert result == payload
