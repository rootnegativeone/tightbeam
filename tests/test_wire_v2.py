"""
End-to-end checks for the v2 frame format produced and consumed by simulation.py.
"""

import base64
import json
import os
import random
import sys

import pytest
import segno

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

    session = sim.ReceiverSession.from_metadata(meta)
    status = _feed(session, package["frames"], 0.2)
    assert status["decode_complete"]
    assert session.recovered_text.encode() == payload
    assert status["raw_len"] == len(payload)
    assert len(status["blocks"]) == meta["k"]
    assert set(status["blocks"]) <= {"1", "2"}


def test_block_states_distinguish_direct_and_repaired():
    package = sim._prepare_package(os.urandom(224 * 20), seed=8)
    session = sim.ReceiverSession.from_metadata(package["metadata"])
    symbols = [f for f in package["frames"] if f["type"] == "symbol"]
    k = package["metadata"]["k"]
    # Lose systematic blocks 3 and 7; repair frames must fill exactly those.
    for frame in symbols:
        if frame["esi"] in (3, 7):
            continue
        status = session.add_frame(frame["qr_value"])
        if frame["esi"] == k - 1:
            assert status["blocks"][3] == "0" and status["blocks"][7] == "0"
            assert status["blocks"].count("1") == k - 2
        if status["decode_complete"]:
            break
    assert status["blocks"][3] == "2" and status["blocks"][7] == "2"


def test_all_frames_use_only_qr_alphanumeric_characters():
    package = sim._prepare_package(os.urandom(3000), seed=1)
    assert {f["type"] for f in package["frames"]} == {"sync", "symbol"}
    for frame in package["frames"]:
        assert set(frame["qr_value"]) <= set(ALPHABET)


def test_sync_frame_round_trips_metadata_and_stays_small():
    package = sim._prepare_package(
        generate_bulk_pos_logs(500 * 1024), seed=1, ecc="M", frame_interval_ms=300
    )
    meta = package["metadata"]
    sync = next(f for f in package["frames"] if f["type"] == "sync")["qr_value"]
    parsed = sim.parse_sync_frame(sync)
    for key, value in meta.items():
        assert parsed[key] == value, key
    assert (parsed["ordinal"], parsed["total"]) == (1, 6)
    # Must never need a bigger QR than the symbol frames do.
    assert len(sync) < len(package["frames"][-1]["qr_value"]) // 3
    assert sim.parse_sync_frame("Y:1:ABC") is None
    assert sim.parse_sync_frame(sync.replace("Y:2:", "Y:3:", 1)) is None


def test_capture_rate_reflects_frame_loss(monkeypatch):
    package = sim._prepare_package(generate_bulk_pos_logs(60 * 1024), seed=2)
    session = sim.ReceiverSession.from_metadata(package["metadata"])
    interval = package["metadata"]["frame_interval_ms"] / 1000
    clock = [100.0]
    monkeypatch.setattr(sim, "perf_counter", lambda: clock[0])
    status = None
    for frame in package["frames"]:
        clock[0] += interval
        if frame["type"] != "symbol" or frame["esi"] % 4 == 3:  # lose 25%
            continue
        status = session.add_frame(frame["qr_value"])
        if status["decode_complete"]:
            break
    assert status["decode_complete"]
    assert 0.70 <= status["capture_rate"] <= 0.80
    assert status["elapsed_s"] > 0


def test_incompressible_binary_payload_returns_base64():
    payload = os.urandom(5000)
    package = sim._prepare_package(payload, seed=9)
    assert package["metadata"]["codec"] == "none"
    session = sim.ReceiverSession.from_metadata(package["metadata"])
    status = _feed(session, package["frames"])
    assert status["recovered_is_base64"]
    assert session.recovered_text == base64.b64encode(payload).decode()


def test_frames_from_another_session_are_rejected():
    a = sim._prepare_package(b"session A " * 200, seed=1)
    b = sim._prepare_package(b"session B " * 200, seed=2)
    session = sim.ReceiverSession.from_metadata(a["metadata"])
    foreign = next(f for f in b["frames"] if f["type"] == "symbol")
    status = session.add_frame(foreign["qr_value"])
    assert not status["newly_added"]
    assert status["rejected"] == {"session_mismatch": 1}

    status = session.add_frame("S:NOTAFRAME")
    assert status["rejected"]["malformed_frame"] == 1


def test_digest_mismatch_fails_finalize():
    package = sim._prepare_package(b"tamper check " * 100, seed=4)
    meta = dict(package["metadata"], sha256="0" * 16)
    status = _feed(sim.ReceiverSession.from_metadata(meta), package["frames"])
    assert status["phase"] == "error"
    assert "sha256" in status["finalize_error"]


def test_browser_entry_points_round_trip():
    package = json.loads(sim.prepare_broadcast(5, 96, "M", 300))
    assert package["metadata"]["block_size"] == 96
    sync = json.loads(sim.receiver_parse_sync(package["frames"][0]["qr_value"]))
    assert json.loads(sim.reset_receiver(json.dumps(sync)))["status"] == "ready"
    for frame in package["frames"]:
        if frame["type"] == "symbol":
            status = json.loads(sim.receiver_add_frame(frame["qr_value"]))
    assert status["decode_complete"]
    recovered = json.loads(sim.receiver_payload())
    assert recovered["text"] == package["payload_text"]
    assert "error" in json.loads(sim.prepare_broadcast(5, 100))
    bulk = json.loads(sim.prepare_broadcast(5, 224, "H", 450, 10))
    assert bulk["metadata"]["raw_len"] == 10 * 1024


def test_reset_receiver_rejects_v1_metadata():
    v1 = {"block_size": 96, "k": 3, "orig_len": 200, "session_id": "TB-00000001"}
    error = json.loads(sim.reset_receiver(json.dumps(v1)))["error"]
    assert "unsupported frame version" in error


def test_parse_symbol_frame_handles_base45_separators():
    payload = bytes(range(256))
    tag, esi, data = sim.parse_symbol_frame(f"S:0000ABCD:42:{sim.b45encode(payload)}")
    assert (tag, esi, data) == ("0000ABCD", 42, payload)
    assert sim.parse_symbol_frame("S:0000ABCD:x:00") is None
    assert sim.parse_symbol_frame("M:{}") is None


@pytest.mark.parametrize(
    "block_size, ecc, max_version",
    [(224, "M", 11), (304, "M", 13), (416, "M", 16), (224, "H", 16), (96, "H", 10)],
)
def test_block_sizes_fit_their_intended_qr_version(block_size, ecc, max_version):
    # Guards the sender's QR size: frames (incl. a 5-digit esi) and sync frames
    # must fit the version each block size was chosen for.
    payload = generate_bulk_pos_logs(100 * 1024)
    package = sim._prepare_package(payload, seed=6, block_size=block_size, ecc=ecc)
    _, tag, _, body = package["frames"][-1]["qr_value"].split(":", 3)
    widest = f"S:{tag}:99999:{body}"
    sync = package["frames"][0]["qr_value"]
    for value in (widest, sync):
        version = segno.make(value, error=ecc.lower(), boost_error=False).version
        assert version <= max_version, (value[:20], version)

    session = sim.ReceiverSession.from_metadata(package["metadata"])
    status = _feed(session, package["frames"], loss=0.1)
    assert status["decode_complete"]
    assert session.recovered_text.encode() == payload


def test_defaults_match_field_tested_settings():
    meta = sim._prepare_package(b"defaults " * 100)["metadata"]
    assert (meta["ecc"], meta["frame_interval_ms"], meta["block_size"]) == (
        "M",
        300,
        224,
    )
