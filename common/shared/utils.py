"""
Utility functions for splitting data into blocks and managing seeds.
"""

import math


def split_blocks(data: bytes, block_size: int) -> list[bytes]:
    """Split data into fixed-size blocks, padding the last block with zeros."""
    if not data:
        return [b"\x00" * block_size]
    blocks = [data[i : i + block_size] for i in range(0, len(data), block_size)]
    if blocks and len(blocks[-1]) < block_size:
        blocks[-1] = blocks[-1] + b"\x00" * (block_size - len(blocks[-1]))
    return blocks


def combine_blocks(blocks: list[bytes], orig_len: int) -> bytes:
    """Combine blocks and truncate to original length."""
    data = b"".join(blocks)
    return data[:orig_len]
