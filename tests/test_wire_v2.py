"""
End-to-end checks for the v2 frame format produced and consumed by simulation.py.
"""

import json
import os
import random
import sys

import pytest

_SIM_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "web", "public", "python")
)
if _SIM_PATH not in sys.path:
    sys.path.append(_SIM_PATH)  # after the repo root, so root `common` wins

import simulation as sim  # noqa: E402

from common.shared.base45 import ALPHABET  # noqa: E402
from common.shared.demo_payloads import generate_bulk_pos_logs  # noqa: E402


def _feed(session, frames, loss=0.0, seed=0):
    rng = random.Random(seed)
    status = None
    for frame in frames:
        if frame["type"] != "symbol" or rng.random() < loss:
            continue
        status = session.add_frame(frame["qr_value"])
        if status["decode_complete"]:
            break
    return status


def test_compressed_logs_round_trip_under_loss():
    payload = generate_bulk_pos_logs(40 * 1024)
    package = sim._prepare_package(payload, seed=3)
    meta = package["metadata"]
    assert meta["v"] == 2 and meta["codec"] == "deflate"
    assert meta["orig_len"] < len(payload) // 4

    status = _feed(sim.ReceiverSession.from_metadata(meta), package["frames"], 0.2)
    assert status["decode_complete"]
    assert status["recovered_text"].encode() == payload
    assert status["raw_len"] == len(payload)


def test_symbol_frames_use_only_qr_alphanumeric_characters():
    package = sim._prepare_package(os.urandom(3000), seed=1)
    for frame in package["frames"]:
        if frame["type"] == "symbol":
            assert set(frame["qr_value"]) <= set(ALPHABET)


def test_incompressible_binary_payload_returns_base64():
    payload = os.urandom(5000)
    package = sim._prepare_package(payload, seed=9)
    assert package["metadata"]["codec"] == "none"
    status = _feed(
        sim.ReceiverSession.from_metadata(package["metadata"]), package["frames"]
    )
    assert status["recovered_is_base64"]
    assert status["recovered_text"] == __import__("base64").b64encode(payload).decode()


def test_frames_from_another_session_are_rejected():
    a = sim._prepare_package(b"session A " * 200, seed=1)
    b = sim._prepare_package(b"session B " * 200, seed=2)
    session = sim.ReceiverSession.from_metadata(a["metadata"])
    foreign = next(f for f in b["frames"] if f["type"] == "symbol")
    status = session.add_frame(foreign["qr_value"])
    assert not status["newly_added"]
    assert status["metrics"]["rejected_symbols"] == {"session_mismatch": 1}

    status = session.add_frame("S:NOTAFRAME")
    assert status["metrics"]["rejected_symbols"]["malformed_frame"] == 1


def test_digest_mismatch_fails_finalize():
    package = sim._prepare_package(b"tamper check " * 100, seed=4)
    meta = dict(package["metadata"], sha256="0" * 16)
    status = _feed(sim.ReceiverSession.from_metadata(meta), package["frames"])
    assert status["phase"] == "error"
    assert "sha256" in status["finalize_error"]


def test_reset_receiver_rejects_v1_metadata():
    v1 = {"block_size": 96, "k": 3, "orig_len": 200, "session_id": "TB-00000001"}
    assert (
        "unsupported frame version"
        in json.loads(sim.reset_receiver(json.dumps(v1)))["error"]
    )
    v2 = sim._prepare_package(b"x" * 500, seed=5)["metadata"]
    assert json.loads(sim.reset_receiver(json.dumps(v2)))["status"] == "ready"


def test_parse_symbol_frame_handles_base45_separators():
    payload = bytes(range(256))
    tag, esi, data = sim.parse_symbol_frame(f"S:0000ABCD:42:{sim.b45encode(payload)}")
    assert (tag, esi, data) == ("0000ABCD", 42, payload)
    assert sim.parse_symbol_frame("S:0000ABCD:x:00") is None
    assert sim.parse_symbol_frame("M:{}") is None
