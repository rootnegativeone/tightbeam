"""
Pyodide entry point that mirrors the browser Send → Encode → Receive flow.

Frame formats are specified in docs/wire_format_v2.md.
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
from common.shared.demo_payloads import generate_bulk_pos_logs
from common.shared.metrics import FountainMetrics

FRAME_VERSION = 2
# 224-byte blocks + 4-byte CRC -> 342 Base45 chars; with the S: header the frame
# is ~359 alphanumeric chars, which fits QR version 16 at ECC-H.
DEFAULT_BLOCK_SIZE = 224
ALLOWED_BLOCK_SIZES = (96, 160, 224)
DEFAULT_ECC = "H"
DEFAULT_FRAME_INTERVAL_MS = 450
DEFAULT_REDUNDANCY = 4
DEFAULT_SEED = 1337

SYNC_PREAMBLE_COUNT = 6
SYNC_INSERT_INTERVAL = 8
# One valid sync frame is enough to lock: it is fully validated by
# parse_sync_frame, and QR's own Reed-Solomon makes misreads negligible.
# (Waiting for 4 distinct sync frames cost ~20 s on the first phone test.)
SYNC_CONFIRMATION_REQUIRED = 1

_CODEC_TO_WIRE = {"deflate": "D", "none": "N"}
_WIRE_TO_CODEC = {v: k for k, v in _CODEC_TO_WIRE.items()}


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


def encode_sync_frame(metadata: Dict[str, object], ordinal: int, total: int) -> str:
    """
    Compact, QR-alphanumeric session announcement.

    Y:{v}:{SESSION}:{k}:{block}:{wire_len}:{raw_len}:{codec}:{SHA16}:{ecc}:
      {interval_ms}:{frames_per_loop}:{symbols_per_loop}:{ordinal}/{total}
    """
    fields = [
        FRAME_VERSION,
        str(metadata["session_id"]).removeprefix("TB-"),
        metadata["k"],
        metadata["block_size"],
        metadata["orig_len"],
        metadata["raw_len"],
        _CODEC_TO_WIRE[str(metadata["codec"])],
        str(metadata["sha256"]).upper(),
        metadata["ecc"],
        metadata["frame_interval_ms"],
        metadata["frames_per_loop"],
        metadata["symbols_per_loop"],
        f"{ordinal}/{total}",
    ]
    return "Y:" + ":".join(str(f) for f in fields)


def parse_sync_frame(value: str) -> Optional[Dict[str, object]]:
    """Inverse of ``encode_sync_frame``; None if malformed or another version."""
    if not value.startswith("Y:"):
        return None
    parts = value[2:].split(":")
    if len(parts) != 13 or parts[0] != str(FRAME_VERSION):
        return None
    try:
        ordinal, total = (int(x) for x in parts[12].split("/"))
        return {
            "v": FRAME_VERSION,
            "session_id": f"TB-{parts[1]}",
            "k": int(parts[2]),
            "block_size": int(parts[3]),
            "orig_len": int(parts[4]),
            "raw_len": int(parts[5]),
            "codec": _WIRE_TO_CODEC[parts[6]],
            "sha256": parts[7].lower(),
            "ecc": parts[8],
            "frame_interval_ms": int(parts[9]),
            "frames_per_loop": int(parts[10]),
            "symbols_per_loop": int(parts[11]),
            "integrity_check": True,
            "ordinal": ordinal,
            "total": total,
            "confirmation_required": SYNC_CONFIRMATION_REQUIRED,
        }
    except (KeyError, ValueError):
        return None


def _prepare_package(
    payload: bytes,
    seed: int = DEFAULT_SEED,
    *,
    block_size: int = DEFAULT_BLOCK_SIZE,
    ecc: str = DEFAULT_ECC,
    frame_interval_ms: int = DEFAULT_FRAME_INTERVAL_MS,
) -> Dict[str, object]:
    if block_size not in ALLOWED_BLOCK_SIZES:
        raise ValueError(f"block_size must be one of {ALLOWED_BLOCK_SIZES}")
    if ecc not in ("L", "M", "Q", "H"):
        raise ValueError("ecc must be one of L, M, Q, H")

    session_seed = random.Random(seed).getrandbits(32)

    compressed = zlib.compress(payload, 9)
    if len(compressed) < len(payload):
        codec, wire = "deflate", compressed
    else:
        codec, wire = "none", payload

    metrics = FountainMetrics()
    encoder = LTEncoder(
        data=wire,
        block_size=block_size,
        systematic=True,
        seed=session_seed,
        integrity_check=True,
        metrics=metrics,
    )
    k = encoder.k
    systematic_count = k
    redundant_count = k + DEFAULT_REDUNDANCY
    symbols_per_loop = systematic_count + redundant_count
    frames_per_loop = (
        SYNC_PREAMBLE_COUNT
        + symbols_per_loop
        + symbols_per_loop // SYNC_INSERT_INTERVAL
    )

    metadata: Dict[str, object] = {
        "v": FRAME_VERSION,
        "block_size": block_size,
        "k": k,
        "orig_len": len(wire),
        "integrity_check": True,
        "session_id": f"TB-{_session_tag(session_seed)}",
        "codec": codec,
        "raw_len": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest()[:16],
        "ecc": ecc,
        "frame_interval_ms": frame_interval_ms,
        "frames_per_loop": frames_per_loop,
        "symbols_per_loop": symbols_per_loop,
    }

    frames: List[Dict[str, object]] = []
    sync_count = 0

    def append_sync() -> None:
        nonlocal sync_count
        ordinal = (sync_count % SYNC_PREAMBLE_COUNT) + 1
        frames.append(
            {
                "sequence": len(frames),
                "type": "sync",
                "ordinal": ordinal,
                "total": SYNC_PREAMBLE_COUNT,
                "qr_value": encode_sync_frame(metadata, ordinal, SYNC_PREAMBLE_COUNT),
            }
        )
        sync_count += 1

    for _ in range(SYNC_PREAMBLE_COUNT):
        append_sync()

    for esi in range(symbols_per_loop):
        idx_list, payload_bytes = encoder.symbol(esi)
        frames.append(
            _encode_symbol_frame(
                sequence=len(frames),
                session_seed=session_seed,
                esi=esi,
                idx_list=idx_list,
                payload=payload_bytes,
                systematic=esi < k,
            )
        )
        if (esi + 1) % SYNC_INSERT_INTERVAL == 0:
            append_sync()

    assert len(frames) == frames_per_loop

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


def _broadcast_json(payload: bytes, seed: int, **settings: object) -> str:
    try:
        package = _prepare_package(payload, seed, **settings)  # type: ignore[arg-type]
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    package["payload_is_base64"] = not _is_utf8(payload)
    return json.dumps(package)


def prepare_broadcast(
    seed: int = DEFAULT_SEED,
    block_size: int = DEFAULT_BLOCK_SIZE,
    ecc: str = DEFAULT_ECC,
    frame_interval_ms: int = DEFAULT_FRAME_INTERVAL_MS,
    sample_kb: int = 0,
) -> str:
    """Broadcast built-in POS logs: the short sample, or ``sample_kb`` of bulk logs."""
    payload = (
        generate_bulk_pos_logs(sample_kb * 1024)
        if sample_kb
        else generate_sample_logs()
    )
    return _broadcast_json(
        payload,
        seed,
        block_size=block_size,
        ecc=ecc,
        frame_interval_ms=frame_interval_ms,
    )


def prepare_broadcast_from_base64(
    payload_b64: str,
    seed: int = DEFAULT_SEED,
    block_size: int = DEFAULT_BLOCK_SIZE,
    ecc: str = DEFAULT_ECC,
    frame_interval_ms: int = DEFAULT_FRAME_INTERVAL_MS,
) -> str:
    try:
        payload = base64.b64decode(payload_b64)
    except (base64.binascii.Error, ValueError) as exc:
        return json.dumps({"error": f"Invalid base64 payload: {exc}"})
    if not payload:
        return json.dumps({"error": "Payload is empty"})
    return _broadcast_json(
        payload,
        seed,
        block_size=block_size,
        ecc=ecc,
        frame_interval_ms=frame_interval_ms,
    )


# Block states reported to the UI grid.
BLOCK_PENDING, BLOCK_DIRECT, BLOCK_REPAIRED = "0", "1", "2"


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
    frame_interval_ms: Optional[int] = None
    frames_per_loop: Optional[int] = None
    symbols_per_loop: Optional[int] = None
    decoder: LTDecoder = field(init=False)
    metrics: FountainMetrics = field(init=False)
    session_tag: str = field(init=False)
    session_seed: int = field(init=False)
    esis_seen: set[int] = field(default_factory=set)
    blocks: List[str] = field(init=False)
    recovered_text: Optional[str] = None
    recovered_is_base64: bool = False
    accepted_symbols: int = 0
    duplicate_frames: int = 0
    first_symbol_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_decode_duration: float = 0.0
    phase: str = "collecting"
    finalize_error: Optional[str] = None
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
        self.blocks = [BLOCK_PENDING] * self.k
        self.start_time = perf_counter()

    @classmethod
    def from_metadata(cls, meta: Dict[str, object]) -> "ReceiverSession":
        def opt_int(key: str) -> Optional[int]:
            value = meta.get(key)
            return int(value) if value is not None else None  # type: ignore[call-overload]

        return cls(
            block_size=int(meta["block_size"]),  # type: ignore[call-overload]
            k=int(meta["k"]),  # type: ignore[call-overload]
            orig_len=int(meta["orig_len"]),  # type: ignore[call-overload]
            integrity_check=bool(meta.get("integrity_check", True)),
            session_id=str(meta["session_id"]),
            codec=str(meta.get("codec", "none")),
            raw_len=opt_int("raw_len"),
            sha256=meta.get("sha256"),  # type: ignore[arg-type]
            frame_interval_ms=opt_int("frame_interval_ms"),
            frames_per_loop=opt_int("frames_per_loop"),
            symbols_per_loop=opt_int("symbols_per_loop"),
        )

    def add_frame(self, value: str) -> Dict[str, object]:
        now = perf_counter()
        parsed = parse_symbol_frame(value)
        if parsed is None:
            self.metrics.record_symbol_rejected("malformed_frame")
            return self._status_dict(newly_added=False)
        tag, esi, payload = parsed
        if tag != self.session_tag:
            self.metrics.record_symbol_rejected("session_mismatch")
            return self._status_dict(newly_added=False)
        if esi in self.esis_seen:
            self.duplicate_frames += 1
            return self._status_dict(newly_added=False)

        indices = symbol_indices(self.session_seed, esi, self.k)
        if not self.decoder.add_symbol(indices, payload):
            return self._status_dict(newly_added=False)

        if self.first_symbol_at is None:
            self.first_symbol_at = now
        self.esis_seen.add(esi)
        self.accepted_symbols += 1
        col = self.decoder.last_pivot_col
        if col is not None:
            self.blocks[col] = BLOCK_DIRECT if esi < self.k else BLOCK_REPAIRED

        self._maybe_decode()
        return self._status_dict(newly_added=True)

    def _capture_stats(self, now: float) -> Dict[str, Optional[float]]:
        """Estimate how many of the symbol frames shown we actually caught."""
        if self.first_symbol_at is None:
            return {"elapsed_s": None, "frames_expected": None, "capture_rate": None}
        end = self.completed_at or now
        elapsed = end - self.first_symbol_at
        expected = None
        rate = None
        if self.frame_interval_ms and self.frames_per_loop and self.symbols_per_loop:
            # Timing starts at the first symbol, i.e. after the sync preamble,
            # so use the symbol share of the rest of the loop.
            shown = elapsed * 1000 / self.frame_interval_ms + 1
            share = self.symbols_per_loop / (self.frames_per_loop - SYNC_PREAMBLE_COUNT)
            expected = shown * share
            rate = min(len(self.esis_seen) / expected, 1.0) if expected else None
        return {
            "elapsed_s": round(elapsed, 2),
            "frames_expected": round(expected, 1) if expected else None,
            "capture_rate": round(rate, 3) if rate is not None else None,
        }

    def _status_dict(self, *, newly_added: bool) -> Dict[str, object]:
        rank = self.decoder.last_rank
        return {
            "newly_added": newly_added,
            "k": self.k,
            "rank": rank,
            "progress": rank / self.k if self.k else 0.0,
            "unique_frames": len(self.esis_seen),
            "duplicate_frames": self.duplicate_frames,
            "redundant_symbols": self.decoder.redundant_symbols,
            "rejected": self.metrics.summary()["rejected_symbols"],
            "blocks": "".join(self.blocks),
            "phase": self.phase,
            "decode_complete": self.recovered_text is not None,
            "recovered_is_base64": self.recovered_is_base64,
            "codec": self.codec,
            "raw_len": self.raw_len,
            "wire_len": self.orig_len,
            "finalize_error": self.finalize_error,
            "decode_ms": round(self.last_decode_duration * 1000, 2),
            **self._capture_stats(perf_counter()),
        }

    def _maybe_decode(self) -> None:
        # Rank is exact, so the solve only runs once it is guaranteed to succeed.
        if self.recovered_text is not None or self.phase == "error":
            return
        if self.decoder.last_rank < self.k:
            return
        start = perf_counter()
        try:
            recovered = self.decoder.decode()
            if recovered is None:
                return
            raw = self._unwrap(recovered)
        except Exception as exc:
            self.finalize_error = str(exc)
            self.phase = "error"
            return
        finally:
            self.last_decode_duration = perf_counter() - start
        try:
            self.recovered_text = raw.decode("utf-8")
        except UnicodeDecodeError:
            self.recovered_text = base64.b64encode(raw).decode("ascii")
            self.recovered_is_base64 = True
        self.blocks = [b if b != BLOCK_PENDING else BLOCK_REPAIRED for b in self.blocks]
        self.completed_at = perf_counter()
        self.phase = "done"

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


def receiver_parse_sync(value: str) -> str:
    """Parse a scanned ``Y:`` frame for the browser (lock + session metadata)."""
    meta = parse_sync_frame(value)
    if meta is None:
        return json.dumps({"error": "not a v2 sync frame"})
    return json.dumps(meta)


def reset_receiver(metadata_json: str) -> str:
    """Initialise a fresh receiver session from parsed sync metadata."""
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
    return json.dumps({"status": "ready", "k": meta["k"]})


def receiver_add_frame(value: str) -> str:
    """Forward a scanned ``S:`` frame from the browser into the fountain decoder."""
    if _active_session is None:
        return json.dumps({"error": "receiver_not_initialised"})
    return json.dumps(_active_session.add_frame(value))


def receiver_payload() -> str:
    """Return the recovered payload once (kept out of per-frame status)."""
    if _active_session is None or _active_session.recovered_text is None:
        return json.dumps({"error": "not_complete"})
    return json.dumps(
        {
            "text": _active_session.recovered_text,
            "is_base64": _active_session.recovered_is_base64,
        }
    )
