# Wire format v2

v2 replaces the v1 frame format (`S:{seq}|{i,j,...}|{hex}`). Sender and receiver deploy together, so there is no compatibility layer. A receiver that gets v1 metadata refuses it and asks for a sender reload.

## Frames

| Prefix | Body | QR mode |
|---|---|---|
| `Y:` | sync JSON: metadata plus `sequence`, `ordinal`, `total`, `confirmation_required` | byte |
| `M:` | metadata JSON | byte |
| `S:` | `{SESSION}:{ESI}:{BASE45}` | **alphanumeric** |

Metadata fields:

- `v` = 2.
- `block_size`, `k`.
- `orig_len`: length of the bytes on the wire, after compression.
- `integrity_check`.
- `session_id` = `TB-{SESSION}`.
- `codec`: `deflate` or `none`.
- `raw_len`.
- `sha256`: first 16 hex characters of the SHA-256 of the raw payload.

Symbol frame fields:

- `SESSION`: 8 uppercase hex characters. This is the 32-bit session seed. A receiver drops symbols whose tag doesn't match its session.
- `ESI`: the encoding symbol id, in decimal.
- `BASE45`: RFC 9285 encoding of `block ‖ crc32(block)`. It is the last field, so its own `:` and space characters can't collide with the separators.

## Symbol → block indices

Frames carry no index lists. Both sides compute `symbol_indices(seed, esi, k)` (`common/fountain/schedule.py`):

- `esi < k`: systematic symbol, indices `[esi]`.
- `esi ≥ k`: repair symbol. Seed splitmix64 with `(seed << 32) | esi`. Its first output picks the degree, `repair_degree(k)` or one less. Later outputs `mod k` pick that many distinct blocks.
- `repair_degree(k) = min(4·bit_length(k) + 4, max(2, ⌈k/2⌉))`.

Everything is integer-only, so another implementation can reproduce it exactly. `tests/test_schedule.py` pins golden values; changing them breaks the wire format.

Why this shape:

- **Index lists cap the degree.** v1 had to send every index, so repair symbols stayed sparse (robust soliton). With systematic symbols first, a lost systematic block can only come back from a repair symbol that covers it, and sparse ones often don't. At 15% loss, v1 needed about 1.7× k frames.
- **Degree grows with log k.** It reaches within about 1–4% of the ideal 1/(1−loss) for k = 50…5000 (`scripts/bench_schedule.py`).
- **Two degrees, not one.** With one fixed even degree, every repair row has even weight, which caps rank at k−1 when no systematic symbol arrives.
- **Cap near k/2.** Degree k would make every repair row identical.

## Sizing

The default block is 224 bytes. With the CRC that is 228 bytes, or 342 Base45 characters. Adding the header gives a frame of about 359 alphanumeric characters, which fits **QR version 16 at ECC-H**. That's the same version v1's redundant frames used, but each frame now carries 2.3× the data. A 96-byte block would fit version 10 if capture needs bigger modules.

## Measured (`scripts/demo_benchmark.py`, 450 ms per frame, sync overhead included)

Payloads are synthetic JSON-lines POS logs (`generate_bulk_pos_logs`); deflate shrinks them about 7×.

| Raw payload | v1 @ 15% loss | v2 @ 15% loss | v2 @ 30% loss |
|---|---|---|---|
| 10 KB | 74 s | 7 s | 8 s |
| 100 KB | 829 s (13.8 min) | 39 s | 45 s |
| 500 KB | 4324 s (72 min) | 188 s (3.1 min) | 222 s |

## Not yet tuned

- **QR ECC level.** H spends about 30% of each code on error correction. The fountain code plus the per-symbol CRC already handle lost or corrupted frames, so M or L could carry about 1.6–2× more per frame. This needs an iPhone capture test with blur and glare first.
- **Sync cadence.** One sync frame every 8 is about 11% airtime. Every symbol frame now carries the session tag, so sync frames could be sent less often.
