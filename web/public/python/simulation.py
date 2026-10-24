"""
Pyodide entry point that mirrors the browser Send → Encode → Receive flow.
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import zlib
from dataclasses import dataclass, field
from time import perf_counter
from typing import Dict, List, Optional

from sim_payload import generate_sample_logs

from common.fountain.decoder import LTDecoder
from common.fountain.encoder import LTEncoder
from common.fountain.schedule import symbol_indices
from common.shared.base45 import b45decode, b45encode
from common.shared.metrics import FountainMetrics

FRAME_VERSION = 2
# 224-byte blocks + 4-byte CRC -> 342 Base45 chars; with the S: header the frame
# is ~359 alphanumeric chars, which fits QR version 16 at ECC-H (the same
# version v1 redundant frames already used, carrying 2.3x the data).
DEFAULT_BLOCK_SIZE = 224
DEFAULT_REDUNDANCY = 4
DEFAULT_SEED = 1337

SYNC_PREAMBLE_COUNT = 6
SYNC_INSERT_INTERVAL = 8
SYNC_CONFIRMATION_REQUIRED = 4


def _encode_metadata_frame(
    sequence: int, metadata: Dict[str, int | str]
) -> Dict[str, object]:
    return {
        "sequence": sequence,
        "type": "meta",
        "content": metadata,
        "qr_value": f"M:{json.dumps(metadata, separators=(',', ':'))}",
    }


def _session_tag(session_seed: int) -> str:
    return f"{session_seed & 0xFFFFFFFF:08X}"


def _encode_symbol_frame(
    sequence: int,
    session_seed: int,
    esi: int,
    idx_list: List[int],
    payload: bytes,
    *,
    systematic: bool,
) -> Dict[str, object]:
    # Every character is in the QR alphanumeric set (Base45 payload last, so
    # its ':' and ' ' characters never collide with the header separators).
    qr_value = f"S:{_session_tag(session_seed)}:{esi}:{b45encode(payload)}"
    return {
        "sequence": sequence,
        "type": "symbol",
        "esi": esi,
        "indices": idx_list,
        "degree": len(idx_list),
        "systematic": systematic,
        "qr_value": qr_value,
    }


def parse_symbol_frame(value: str) -> Optional[tuple[str, int, bytes]]:
    """Split an ``S:`` frame into (session tag, esi, payload); None if malformed."""
    if not value.startswith("S:"):
        return None
    parts = value[2:].split(":", 2)
    if len(parts) != 3 or not parts[1].isdigit():
        return None
    try:
        payload = b45decode(parts[2])
    except ValueError:
        return None
    return parts[0], int(parts[1]), payload


def _encode_sync_frame(
    sequence: int, ordinal: int, total: int, metadata: Dict[str, int | str]
) -> Dict[str, object]:
    payload = {
        "sequence": sequence,
        "ordinal": ordinal,
        "total": total,
        **metadata,
        "confirmation_required": SYNC_CONFIRMATION_REQUIRED,
    }
    return {
        "sequence": sequence,
        "type": "sync",
        "ordinal": ordinal,
        "total": total,
        "content": payload,
        "qr_value": f"Y:{json.dumps(payload, separators=(',', ':'))}",
    }


def _prepare_package(payload: bytes, seed: int = DEFAULT_SEED) -> Dict[str, object]:
    session_seed = random.Random(seed).getrandbits(32)

    compressed = zlib.compress(payload, 9)
    if len(compressed) < len(payload):
        codec, wire = "deflate", compressed
    else:
        codec, wire = "none", payload

    metrics = FountainMetrics()
    encoder = LTEncoder(
        data=wire,
        block_size=DEFAULT_BLOCK_SIZE,
        systematic=True,
        seed=session_seed,
        integrity_check=True,
        metrics=metrics,
    )
    k = encoder.k
    systematic_count = k
    redundant_count = k + DEFAULT_REDUNDANCY

    metadata = {
        "v": FRAME_VERSION,
        "block_size": DEFAULT_BLOCK_SIZE,
        "k": k,
        "orig_len": len(wire),
        "integrity_check": True,
        "session_id": f"TB-{_session_tag(session_seed)}",
        "codec": codec,
        "raw_len": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest()[:16],
    }

    frames: List[Dict[str, object]] = []
    sequence = 0

    sync_count = 0

    def append_sync() -> None:
        nonlocal sequence, sync_count
        ordinal = (sync_count % SYNC_PREAMBLE_COUNT) + 1
        frames.append(
            _encode_sync_frame(
                sequence=sequence,
                ordinal=ordinal,
                total=SYNC_PREAMBLE_COUNT,
                metadata=metadata,
            )
        )
        sequence += 1
        sync_count += 1

    for _ in range(SYNC_PREAMBLE_COUNT):
        append_sync()

    frames.append(_encode_metadata_frame(sequence=sequence, metadata=metadata))
    sequence += 1

    since_last_sync = 0
    for esi in range(systematic_count + redundant_count):
        idx_list, payload_bytes = encoder.symbol(esi)
        frames.append(
            _encode_symbol_frame(
                sequence=sequence,
                session_seed=session_seed,
                esi=esi,
                idx_list=idx_list,
                payload=payload_bytes,
                systematic=esi < k,
            )
        )
        sequence += 1
        since_last_sync += 1

        if since_last_sync >= SYNC_INSERT_INTERVAL:
            append_sync()
            since_last_sync = 0

    return {
        "seed": seed,
        "payload_text": _safe_decode_text(payload),
        "metadata": metadata,
        "frames": frames,
        "total_frames": len(frames),
        "systematic_count": systematic_count,
        "redundant_count": redundant_count,
        "sync": {
            "preamble_count": SYNC_PREAMBLE_COUNT,
            "interval": SYNC_INSERT_INTERVAL,
            "confirmation_required": SYNC_CONFIRMATION_REQUIRED,
        },
    }


def _is_utf8(payload: bytes) -> bool:
    try:
        payload.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _safe_decode_text(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return base64.b64encode(payload).decode("ascii")


def _render_package(package: Dict[str, object]) -> str:
    return json.dumps(package)


def prepare_broadcast(seed: int = DEFAULT_SEED) -> str:
    payload = generate_sample_logs()
    package = _prepare_package(payload=payload, seed=seed)
    return _render_package(package)


def prepare_broadcast_from_base64(payload_b64: str, seed: int = DEFAULT_SEED) -> str:
    try:
        payload = base64.b64decode(payload_b64)
    except (base64.binascii.Error, ValueError) as exc:
        return json.dumps({"error": f"Invalid base64 payload: {exc}"})

    if not payload:
        return json.dumps({"error": "Payload is empty"})

    package = _prepare_package(payload=payload, seed=seed)
    package["payload_is_base64"] = not _is_utf8(payload)
    return _render_package(package)


@dataclass
class ReceiverSession:
    block_size: int
    k: int
    orig_len: int
    integrity_check: bool
    session_id: str
    codec: str = "none"
    raw_len: Optional[int] = None
    sha256: Optional[str] = None
    decoder: LTDecoder = field(init=False)
    metrics: FountainMetrics = field(init=False)
    session_tag: str = field(init=False)
    session_seed: int = field(init=False)
    esis_seen: set[int] = field(default_factory=set)
    unique_indices: set[int] = field(default_factory=set)
    recovered_text: Optional[str] = None
    recovered_is_base64: bool = False
    accepted_symbols: int = 0
    last_decode_attempt: float = 0.0
    last_decode_duration: float = 0.0
    phase: str = "collecting"
    decode_error: Optional[str] = None
    finalize_status: str = "idle"
    finalize_started_at: Optional[float] = None
    finalize_error: Optional[str] = None
    phase_started_at: float = field(init=False)
    phase_durations: Dict[str, float] = field(
        default_factory=lambda: {
            "collecting": 0.0,
            "solving": 0.0,
            "finalizing": 0.0,
            "done": 0.0,
            "error": 0.0,
        }
    )
    start_time: float = field(init=False)

    def __post_init__(self) -> None:
        self.metrics = FountainMetrics()
        self.decoder = LTDecoder(
            block_size=self.block_size,
            k=self.k,
            orig_len=self.orig_len,
            integrity_check=self.integrity_check,
            metrics=self.metrics,
        )
        self.session_tag = self.session_id.removeprefix("TB-").upper()
        self.session_seed = int(self.session_tag, 16)
        self.start_time = perf_counter()
        self.phase_started_at = self.start_time

    @classmethod
    def from_metadata(cls, meta: Dict[str, object]) -> "ReceiverSession":
        return cls(
            block_size=int(meta["block_size"]),  # type: ignore[call-overload]
            k=int(meta["k"]),  # type: ignore[call-overload]
            orig_len=int(meta["orig_len"]),  # type: ignore[call-overload]
            integrity_check=bool(meta.get("integrity_check", True)),
            session_id=str(meta["session_id"]),
            codec=str(meta.get("codec", "none")),
            raw_len=meta.get("raw_len"),  # type: ignore[arg-type]
            sha256=meta.get("sha256"),  # type: ignore[arg-type]
        )

    def add_frame(self, value: str) -> Dict[str, object]:
        now = perf_counter()
        parsed = parse_symbol_frame(value)
        if parsed is None:
            self.metrics.record_symbol_rejected("malformed_frame")
            return self._status_dict(redundant=False, newly_added=False)
        tag, esi, payload = parsed
        if tag != self.session_tag:
            self.metrics.record_symbol_rejected("session_mismatch")
            return self._status_dict(redundant=False, newly_added=False)
        if esi in self.esis_seen:
            return self._status_dict(redundant=True, newly_added=False)

        indices = symbol_indices(self.session_seed, esi, self.k)
        accepted = self.decoder.add_symbol(indices, payload)
        if not accepted:
            return self._status_dict(redundant=False, newly_added=False)

        self.esis_seen.add(esi)
        self.unique_indices.update(indices)
        self.accepted_symbols += 1

        self._maybe_attempt_decode(now)

        return self._status_dict(redundant=False, newly_added=True)

    def _status_dict(self, *, redundant: bool, newly_added: bool) -> Dict[str, object]:
        coverage = len(self.unique_indices) / self.k if self.k else 0.0
        summary = self.metrics.summary()
        phase_durations = dict(self.phase_durations)
        now = perf_counter()
        if self.phase in phase_durations:
            phase_durations[self.phase] += now - self.phase_started_at
        return {
            "redundant": redundant,
            "newly_added": newly_added,
            "symbols_observed": len(self.esis_seen),
            "unique_symbols": len(self.unique_indices),
            "accepted_symbols_total": self.accepted_symbols,
            "accepted_unique_symbols": len(self.unique_indices),
            "k": self.k,
            "rank_estimate": self.decoder.last_rank,
            "unknowns_remaining": max(self.k - self.decoder.last_rank, 0),
            "coverage": coverage,
            "decode_complete": self.recovered_text is not None,
            "recovered_text": self.recovered_text,
            "recovered_is_base64": self.recovered_is_base64,
            "codec": self.codec,
            "raw_len": self.raw_len,
            "phase": self.phase,
            "last_decode_attempt_ms": (
                round((self.last_decode_attempt - self.start_time) * 1000, 1)
                if self.last_decode_attempt
                else None
            ),
            "last_decode_attempt_age_ms": (
                round((now - self.last_decode_attempt) * 1000, 1)
                if self.last_decode_attempt
                else None
            ),
            "last_decode_duration_ms": (
                round(self.last_decode_duration * 1000, 1)
                if self.last_decode_duration
                else None
            ),
            "phase_durations_ms": {
                key: round(value * 1000, 1) for key, value in phase_durations.items()
            },
            "decode_error": self.decode_error,
            "finalize_status": self.finalize_status,
            "finalize_error": self.finalize_error,
            "finalize_elapsed_ms": (
                round((now - self.finalize_started_at) * 1000, 1)
                if self.finalize_started_at and self.finalize_status == "in_progress"
                else None
            ),
            "metrics": summary,
        }

    def _set_phase(self, next_phase: str) -> None:
        if next_phase == self.phase:
            return
        now = perf_counter()
        if self.phase in self.phase_durations:
            self.phase_durations[self.phase] += now - self.phase_started_at
        self.phase = next_phase
        self.phase_started_at = now

    def _maybe_attempt_decode(self, now: float) -> None:
        if self.recovered_text is not None or self.phase == "error":
            return
        # The decoder tracks exact rank incrementally, so a solve only runs
        # once it is guaranteed to succeed.
        if self.decoder.last_rank < self.k:
            self._set_phase("collecting")
            return

        self._set_phase("solving")
        self.last_decode_attempt = now
        attempt_start = perf_counter()
        try:
            recovered = self.decoder.decode()
        except Exception as exc:
            self.last_decode_duration = perf_counter() - attempt_start
            self.decode_error = str(exc)
            self.finalize_status = "error"
            self.finalize_error = self.decode_error
            self._set_phase("error")
            return

        self.last_decode_duration = perf_counter() - attempt_start
        if recovered is not None:
            self._finalize_recovery(recovered)
        else:
            self._set_phase("collecting")

    def _finalize_recovery(self, recovered: bytes) -> None:
        self._set_phase("finalizing")
        if self.finalize_status == "idle":
            self.finalize_status = "in_progress"
            self.finalize_started_at = perf_counter()
        try:
            raw = self._unwrap(recovered)
            try:
                self.recovered_text = raw.decode("utf-8")
            except UnicodeDecodeError:
                self.recovered_text = base64.b64encode(raw).decode("ascii")
                self.recovered_is_base64 = True
            self.finalize_status = "done"
            self._set_phase("done")
        except Exception as exc:
            self.finalize_status = "error"
            self.finalize_error = str(exc)
            self._set_phase("error")

    def _unwrap(self, recovered: bytes) -> bytes:
        """Undo transport compression and verify the whole-payload digest."""
        if self.codec == "deflate":
            raw = zlib.decompress(recovered)
        elif self.codec == "none":
            raw = recovered
        else:
            raise ValueError(f"unsupported codec {self.codec!r}")
        if self.raw_len is not None and len(raw) != self.raw_len:
            raise ValueError(f"length mismatch: {len(raw)} != {self.raw_len}")
        if self.sha256 and hashlib.sha256(raw).hexdigest()[:16] != self.sha256:
            raise ValueError("sha256 mismatch")
        return raw


_active_session: Optional[ReceiverSession] = None


def reset_receiver(metadata_json: str) -> str:
    """Initialise a fresh receiver session from a sync/metadata frame's JSON."""
    global _active_session
    try:
        meta = json.loads(metadata_json)
    except ValueError as exc:
        return json.dumps({"error": f"invalid metadata: {exc}"})
    if meta.get("v") != FRAME_VERSION:
        return json.dumps(
            {"error": f"unsupported frame version {meta.get('v')!r}; reload sender"}
        )
    _active_session = ReceiverSession.from_metadata(meta)
    return json.dumps(
        {"status": "ready", "block_size": meta["block_size"], "k": meta["k"]}
    )


def receiver_add_frame(value: str) -> str:
    """Forward a scanned ``S:`` frame from the browser into the fountain decoder."""
    if _active_session is None:
        return json.dumps({"error": "receiver_not_initialised"})
    return json.dumps(_active_session.add_frame(value))


def receiver_status() -> str:
    """Return the current receiver session status."""
    if _active_session is None:
        return json.dumps({"error": "receiver_not_initialised"})
    return json.dumps(_active_session._status_dict(redundant=False, newly_added=False))


def simulate_transfer(seed: int = DEFAULT_SEED) -> str:
    """
    Compatibility helper mirroring the previous testing-oriented payload.
    """
    package = json.loads(prepare_broadcast(seed))
    metadata = package["metadata"]

    reset_receiver(json.dumps(metadata))

    timeline = []
    for frame in package["frames"]:
        if frame["type"] != "symbol":
            continue
        status = json.loads(receiver_add_frame(frame["qr_value"]))
        timeline.append(
            {
                "sequence": frame["sequence"],
                "coverage": status["coverage"],
                "decode_complete": status["decode_complete"],
            }
        )

    package["timeline"] = timeline
    package["receiver_summary"] = json.loads(receiver_status())
    return json.dumps(package)
