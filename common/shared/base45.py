"""
Base45 (RFC 9285): binary-to-text encoding using only the QR alphanumeric set.

QR alphanumeric mode packs 2 characters into 11 bits, and Base45 packs 2 bytes
into 3 characters, so a Base45 payload costs ~16.5 bits per 16 bits of data
versus 32 bits for hex in byte mode.
"""

from __future__ import annotations

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
_LOOKUP = {char: value for value, char in enumerate(ALPHABET)}


def b45encode(data: bytes) -> str:
    out = []
    for i in range(0, len(data) - 1, 2):
        n = data[i] * 256 + data[i + 1]
        out.append(ALPHABET[n % 45])
        out.append(ALPHABET[n // 45 % 45])
        out.append(ALPHABET[n // 2025])
    if len(data) % 2:
        n = data[-1]
        out.append(ALPHABET[n % 45])
        out.append(ALPHABET[n // 45])
    return "".join(out)


def b45decode(text: str) -> bytes:
    try:
        values = [_LOOKUP[char] for char in text]
    except KeyError as exc:
        raise ValueError(f"invalid base45 character {exc.args[0]!r}") from None
    if len(values) % 3 == 1:
        raise ValueError("invalid base45 length")

    out = bytearray()
    for i in range(0, len(values), 3):
        chunk = values[i : i + 3]
        if len(chunk) == 3:
            n = chunk[0] + chunk[1] * 45 + chunk[2] * 2025
            if n > 0xFFFF:
                raise ValueError("invalid base45 triplet")
            out.extend((n >> 8, n & 0xFF))
        else:
            n = chunk[0] + chunk[1] * 45
            if n > 0xFF:
                raise ValueError("invalid base45 pair")
            out.append(n)
    return bytes(out)


__all__ = ["ALPHABET", "b45decode", "b45encode"]
