"""
Pyodide entry point that mirrors the browser Send → Encode → Receive flow.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from common.fountain.encoder import LTEncoder
from common.fountain.decoder import LTDecoder
from common.shared.metrics import FountainMetrics
from sim_payload import generate_sample_logs

DEFAULT_BLOCK_SIZE = 48
DEFAULT_REDUNDANCY = 4
DEFAULT_SEED = 1337

SYNC_PREAMBLE_COUNT = 4
SYNC_INSERT_INTERVAL = 8
SYNC_CONFIRMATION_REQUIRED = 3


def _normalize_indices(idxs: int | Iterable[int]) -> List[int]:
    if isinstance(idxs, int):
        return [idxs]
    return list(idxs)


def _encode_metadata_frame(
    sequence: int, metadata: Dict[str, int | str]
) -> Dict[str, object]:
    return {
        "sequence": sequence,
        "type": "meta",
        "content": metadata,
        "qr_value": f"M:{json.dumps(metadata, separators=(',', ':'))}",
    }


def _encode_symbol_frame(
    sequence: int,
    idx_list: List[int],
    payload: bytes,
    *,
    systematic: bool,
) -> Dict[str, object]:
    payload_hex = payload.hex()
    indices_part = ",".join(str(i) for i in idx_list)
    qr_value = f"S:{sequence}|{indices_part}|{payload_hex}"
    return {
        "sequence": sequence,
        "type": "symbol",
        "indices": idx_list,
        "degree": len(idx_list),
        "payload_hex": payload_hex,
        "systematic": systematic,
        "qr_value": qr_value,
    }


def _encode_sync_frame(
    sequence: int, ordinal: int, total: int, metadata: Dict[str, int | str]
) -> Dict[str, object]:
    payload = {
        "sequence": sequence,
        "ordinal": ordinal,
        "total": total,
        "block_size": metadata["block_size"],
        "k": metadata["k"],
        "orig_len": metadata["orig_len"],
        "integrity_check": metadata["integrity_check"],
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


def prepare_broadcast(seed: int = DEFAULT_SEED) -> str:
    """
    Create a broadcast package containing metadata and QR symbol frames.
    """
    random.seed(seed)
    payload = generate_sample_logs()

    metrics = FountainMetrics()
    encoder = LTEncoder(
        data=payload,
        block_size=DEFAULT_BLOCK_SIZE,
        systematic=True,
        integrity_check=True,
        metrics=metrics,
    )

    systematic_symbols = list(encoder.emit_systematic())
    redundant_symbols = encoder.encode(len(encoder.blocks) + DEFAULT_REDUNDANCY)
    all_symbols = systematic_symbols + redundant_symbols

    metadata = {
        "block_size": DEFAULT_BLOCK_SIZE,
        "k": len(encoder.blocks),
        "orig_len": len(payload),
        "integrity_check": True,
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
    for offset, (idxs, payload_bytes) in enumerate(all_symbols):
        idx_list = _normalize_indices(idxs)
        frames.append(
            _encode_symbol_frame(
                sequence=sequence,
                idx_list=idx_list,
                payload=payload_bytes,
                systematic=offset < len(systematic_symbols),
            )
        )
        sequence += 1
        since_last_sync += 1

        if since_last_sync >= SYNC_INSERT_INTERVAL:
            append_sync()
            since_last_sync = 0

    package = {
        "seed": seed,
        "payload_text": payload.decode("utf-8"),
        "metadata": metadata,
        "frames": frames,
        "total_frames": len(frames),
        "systematic_count": len(systematic_symbols),
        "redundant_count": len(redundant_symbols),
        "sync": {
            "preamble_count": SYNC_PREAMBLE_COUNT,
            "interval": SYNC_INSERT_INTERVAL,
            "confirmation_required": SYNC_CONFIRMATION_REQUIRED,
        },
    }
    return json.dumps(package)


@dataclass
class ReceiverSession:
    block_size: int
    k: int
    orig_len: int
    integrity_check: bool
    decoder: LTDecoder = field(init=False)
    metrics: FountainMetrics = field(init=False)
    sequences_seen: set[int] = field(default_factory=set)
    unique_indices: set[int] = field(default_factory=set)
    recovered_text: Optional[str] = None

    def __post_init__(self) -> None:
        self.metrics = FountainMetrics()
        self.decoder = LTDecoder(
            block_size=self.block_size,
            k=self.k,
            orig_len=self.orig_len,
            integrity_check=self.integrity_check,
            metrics=self.metrics,
        )

    def add_symbol(
        self, sequence: int, indices: List[int], payload_hex: str
    ) -> Dict[str, object]:
        if sequence in self.sequences_seen:
            return self._status_dict(redundant=True, newly_added=False)

        payload = bytes.fromhex(payload_hex)
        self.decoder.add_symbol(indices, payload)
        self.sequences_seen.add(sequence)
        self.unique_indices.update(indices)

        recovered = self.decoder.decode()
        if recovered is not None:
            self.recovered_text = recovered.decode("utf-8")

        return self._status_dict(redundant=False, newly_added=True)

    def _status_dict(self, *, redundant: bool, newly_added: bool) -> Dict[str, object]:
        coverage = len(self.unique_indices) / self.k if self.k else 0.0
        summary = self.metrics.summary()
        return {
            "redundant": redundant,
            "newly_added": newly_added,
            "symbols_observed": len(self.sequences_seen),
            "unique_symbols": len(self.unique_indices),
            "coverage": coverage,
            "decode_complete": self.recovered_text is not None,
            "recovered_text": self.recovered_text,
            "metrics": summary,
        }


_active_session: Optional[ReceiverSession] = None


def reset_receiver(
    block_size: int, k: int, orig_len: int, integrity_check: bool = True
) -> str:
    """Initialise a fresh receiver session with supplied metadata."""
    global _active_session
    _active_session = ReceiverSession(
        block_size=block_size,
        k=k,
        orig_len=orig_len,
        integrity_check=integrity_check,
    )
    return json.dumps({"status": "ready", "block_size": block_size, "k": k})


def receiver_add_symbol(sequence: int, indices: List[int], payload_hex: str) -> str:
    """Forward a decoded symbol from the browser receiver into the fountain decoder."""
    if _active_session is None:
        return json.dumps({"error": "receiver_not_initialised"})

    status = _active_session.add_symbol(sequence, indices, payload_hex)
    return json.dumps(status)


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

    reset_receiver(
        block_size=metadata["block_size"],
        k=metadata["k"],
        orig_len=metadata["orig_len"],
        integrity_check=metadata.get("integrity_check", True),
    )

    timeline = []
    for frame in package["frames"]:
        if frame["type"] != "symbol":
            continue
        sequence = frame["sequence"]
        indices = frame["indices"]
        payload_hex = frame["payload_hex"]
        status = json.loads(receiver_add_symbol(sequence, indices, payload_hex))
        timeline.append(
            {
                "sequence": sequence,
                "coverage": status["coverage"],
                "decode_complete": status["decode_complete"],
            }
        )

    package["timeline"] = timeline
    package["receiver_summary"] = json.loads(receiver_status())
    return json.dumps(package)
