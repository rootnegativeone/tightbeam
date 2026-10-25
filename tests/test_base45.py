import os

import pytest

from common.shared.base45 import ALPHABET, b45decode, b45encode


@pytest.mark.parametrize(
    "raw, encoded",
    [  # RFC 9285 section 4.3 examples
        (b"AB", "BB8"),
        (b"Hello!!", "%69 VD92EX0"),
        (b"base-45", "UJCLQE7W581"),
        (b"ietf!", "QED8WEX0"),
        (b"", ""),
    ],
)
def test_rfc_vectors(raw, encoded):
    assert b45encode(raw) == encoded
    assert b45decode(encoded) == raw


def test_round_trip_random_bytes_stays_in_qr_alphanumeric_set():
    data = os.urandom(229)
    text = b45encode(data)
    assert set(text) <= set(ALPHABET)
    assert len(text) == 3 * (len(data) // 2) + 2 * (len(data) % 2)
    assert b45decode(text) == data


@pytest.mark.parametrize("bad", ["GGW", "a", "ZZZZ", "AB!"])
def test_rejects_invalid_input(bad):
    with pytest.raises(ValueError):
        b45decode(bad)
