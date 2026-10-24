# AGENTS.md

Tightbeam moves data over a one-way optical link: a sender displays a looping stream of QR codes carrying LT fountain-coded symbols, and a camera receiver reconstructs the payload no matter which frames it misses. The target use case is pulling logs off POS terminals and other air-gapped devices.

## Layout
- `common/`: **source of truth** for the Python core (encoder, incremental GF(2) decoder, metrics). Stdlib only, no third-party deps.
- `web/`: Vite + React app (`web/src/App.tsx`) that runs the Python core in-browser via Pyodide (`web/src/lib/pyodide.ts`).
  - `web/public/python/simulation.py` and `sim_payload.py`: Pyodide entry points (sender package builder + `ReceiverSession`).
  - `web/public/python/common/` is **generated** (gitignored) by `npm run sync-python`. Never edit it; edit `common/` instead.
  - When you add a Python module, also add it to `PYTHON_FILES` in `web/src/lib/pyodide.ts`.
- `decoder/reassembler.py`: compatibility re-export of `LTDecoder`.
- `scripts/`: `demo_assert_complete.py` (10KB end-to-end check), `demo_benchmark.py`, `bench_channel.py`.
- `docs/`: design and performance notes.

## Commands
```bash
pip install -r requirements-dev.txt
pytest -q
black --check . && mypy common/fountain
python scripts/demo_assert_complete.py
cd web && npm install && npm run dev     # or: npm run build
```
CI (`.github/workflows/ci.yml`) runs all of the above plus the web build.

## Deployment
Vercel deploys `web/` to https://tightbeam.vercel.app. The build reads `../common` via `sync-python`, so the Vercel project must keep "Include files outside the root directory" enabled.

## Wire format (encoder and receiver must change together)
- `Y:{json}`: sync frame (session metadata, repeated as a preamble and every 8 frames)
- `M:{json}`: metadata frame (`block_size`, `k`, `orig_len`, `integrity_check`, `session_id`)
- `S:{seq}|{i,j,...}|{hex(block + crc32)}`: symbol frame
Producers: `simulation.py` (`_encode_*_frame`). Consumer: `App.tsx` `processValue` → `handleSymbol` → `receiver_add_symbol`.

## Conventions
- Never use the module-global `random`. Pass a `random.Random` instance (`LTEncoder(rng=...)`).
- Keep the `LTDecoder` public API stable: `add_symbol`, `decode`, `rank`, `is_complete`, `last_rank`.
- The decoder is incremental. Rank is exact after every `add_symbol`, so only call `decode()` once `rank == k`.
- Payload sizes the demo should handle: 10KB–500KB. Check the timing of anything on the receive path; Pyodide runs on the main thread.
