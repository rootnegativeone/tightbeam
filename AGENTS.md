# AGENTS.md

Tightbeam moves data over a one-way optical link: a sender displays a looping stream of QR codes carrying LT fountain-coded symbols, and a camera receiver reconstructs the payload no matter which frames it misses. The target use case is pulling logs off POS terminals and other air-gapped devices.

## Layout
- `common/`: **source of truth** for the Python core (encoder, incremental GF(2) decoder, metrics). Stdlib only, no third-party deps.
- `web/`: Vite + React app (`web/src/App.tsx`) that runs the Python core in-browser via Pyodide (`web/src/lib/pyodide.ts`).
  - `web/public/python/simulation.py` and `sim_payload.py`: Pyodide entry points (sender package builder + `ReceiverSession`).
  - `web/public/python/common/` is **generated** (gitignored) by `npm run sync-python`. Never edit it; edit `common/` instead.
  - When you add a Python module, also add it to `PYTHON_FILES` in `web/src/lib/pyodide.ts`.
- `decoder/reassembler.py`: compatibility re-export of `LTDecoder`.
- `scripts/`: `demo_assert_complete.py` (10KB end-to-end check), `demo_benchmark.py` (v2 transfer times by size/loss), `bench_schedule.py`, `bench_channel.py`.
- `docs/`: design and performance notes.

## Commands
```bash
pip install -r requirements-dev.txt
pytest -q
black --check . && mypy common/fountain
python scripts/demo_assert_complete.py
cd web && npm install && npm run dev     # or: npm run typecheck / npm run build
```
CI (`.github/workflows/ci.yml`) runs all of the above plus the web build.

## Deployment
Vercel deploys `web/` to https://tightbeam.vercel.app. The build reads `../common` via `sync-python`, so the Vercel project must keep "Include files outside the root directory" enabled.

## Wire format v2 (encoder and receiver must change together)
Full spec: `docs/wire_format_v2.md`.
- `Y:{json}`: sync frame (metadata, repeated as a preamble and every 8 frames)
- `M:{json}`: metadata (`v`, `block_size`, `k`, `orig_len` = wire bytes, `session_id`, `codec`, `raw_len`, `sha256` prefix)
- `S:{SESSION}:{ESI}:{base45(block + crc32)}`: symbol frame. All QR-alphanumeric characters. No index list; both sides derive indices with `common/fountain/schedule.symbol_indices(seed, esi, k)`.
Producer: `simulation._prepare_package`. Consumer: `App.tsx` `processValue` → `handleSymbol` → `receiver_add_frame` (parsing happens in Python).
`tests/test_schedule.py` pins the golden schedule values; changing them is a wire-format break.

## Conventions
- Never use the module-global `random`. The encoder is deterministic given `seed`; anything else random takes a `random.Random` instance.
- Keep the `LTDecoder` public API stable: `add_symbol`, `decode`, `rank`, `is_complete`, `last_rank`.
- The decoder is incremental. Rank is exact after every `add_symbol`, so only call `decode()` once `rank == k`.
- `vite build` does not type-check; run `npm run typecheck` (CI does).
- iPhone Safari has no BarcodeDetector, so iPhones always use the ZXing fallback path in `startCamera`. Test changes there on a real phone.
- Payload sizes the demo should handle: 10KB–500KB raw (deflate shrinks logs ~7x). Check the timing of anything on the receive path; Pyodide runs on the main thread.
