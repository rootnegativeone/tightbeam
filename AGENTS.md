# AGENTS.md

Tightbeam moves data over a one-way optical link: a sender displays a looping stream of QR codes carrying LT fountain-coded symbols, and a camera receiver reconstructs the payload no matter which frames it misses. The target use case is pulling logs off POS terminals and other air-gapped devices.

## Layout
- `common/`: **source of truth** for the Python core (encoder, incremental GF(2) decoder, metrics). Stdlib only, no third-party deps.
- `web/`: Vite + React app that runs the Python core in-browser via Pyodide (`web/src/lib/pyodide.ts`).
  - `web/public/python/simulation.py` and `sim_payload.py`: Pyodide entry points (sender package builder + `ReceiverSession`).
  - `web/public/python/common/` is **generated** (gitignored) by `npm run sync-python`. Never edit it; edit `common/` instead.
  - When you add a Python module, also add it to `PYTHON_FILES` in `web/src/lib/pyodide.ts`.
- `decoder/reassembler.py`: compatibility re-export of `LTDecoder`.
- `scripts/`: `demo_assert_complete.py` (10KB end-to-end check), `demo_benchmark.py` (v2 transfer times by size/loss), `bench_schedule.py`, `bench_channel.py`.
- `docs/`: design and performance notes; `field_test_plan.md` is the phone test protocol.

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
Full spec: `docs/wire_format_v2.md`. Every frame is QR-alphanumeric.
- `Y:2:{SESSION}:{k}:…:{ordinal}/{total}`: compact sync/metadata frame (`simulation.encode_sync_frame` / `parse_sync_frame`).
- `S:{SESSION}:{ESI}:{base45(block + crc32)}`: symbol frame with no index list. Both sides derive indices with `common/fountain/schedule.symbol_indices(seed, esi, k)`.
- The sender pins every frame to one QR version (`web/src/lib/qr.ts` `commonVersion`), so keep sync frames smaller than symbol frames.
Golden schedule values are pinned in `tests/test_schedule.py`; changing them is a wire-format break.

## Web UI
- `web/src/sender/SenderView.tsx`; `web/src/receiver/` (`useScanner` = camera/QR detection, `useTransfer` = lock + session, `report.ts` = test report).
- Receiver layout rule: the camera viewfinder is first and has a fixed aspect ratio. Never render content above it that changes height while scanning.
- Routes: `#send`, `#receive`. The sender shows a QR code of `…/#receive` so a phone opens straight to the receiver.

## Conventions
- Never use the module-global `random`. The encoder is deterministic given `seed`; anything else random takes a `random.Random` instance.
- Keep the `LTDecoder` public API stable: `add_symbol`, `decode`, `rank`, `is_complete`, `last_rank`.
- The decoder is incremental. Rank is exact after every `add_symbol`, so only call `decode()` once `rank == k`.
- `vite build` does not type-check; run `npm run typecheck` (CI does).
- QR decoding (`web/src/receiver/useScanner.ts`): the native `BarcodeDetector` where it exists; otherwise zxing-cpp compiled to WebAssembly via the `barcode-detector` ponyfill. iOS browsers (Safari *and* Chrome) never have the native detector, so iPhones always use the WASM path. The WASM is bundled and served from `/assets/`, not the package's CDN default. Don't reintroduce the ZXing JavaScript port: in testing it failed to find 3–31% of perfectly rendered dense codes.
- To test the iPhone path in desktop Chrome, inject `delete window.BarcodeDetector` before page load. The receiver's Diagnostics section shows which decoder is active.
- The receiver locks on the first valid sync frame and replays symbol frames seen before lock (`useTransfer`).
- Payload sizes the demo should handle: 10KB–500KB raw (deflate shrinks logs ~7x). Check the timing of anything on the receive path; Pyodide runs on the main thread.
