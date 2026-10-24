# Demo Throughput Note (10KB)

## What Was Wrong
- Redundancy stream duplicated systematic symbols because the encoder did not advance its internal counter after `emit_systematic()`.
- The receiver attempted a full decode on every accepted symbol, causing extra work and UI jitter near the end.

## What Changed
- `emit_systematic()` now advances the encoder’s `generated` counter so redundancy symbols are truly LT-coded.
- Receiver decode was gated by time and symbol count. (Superseded: the decoder is now incremental, tracks exact rank on every symbol, and solves only once rank reaches k. See "Incremental decoder" below.)
- Receiver UI now surfaces phase (Collecting → Solving → Finalizing) and decode attempt timing.
- Demo cadence is 450ms per frame, block size is 96 bytes, sync insert interval is 8 frames.

## Before / After (Simulated)
Baseline (old settings, simulated @ 650ms, block size 48):
- 0% loss: ~146.9s, 1.54 symbols/sec, complete
- 10% loss: ~242.5s, 1.33 symbols/sec, complete

After changes (simulated @ 450ms, block size 96):
- 0% loss: 53.55s, 2.22 symbols/sec, complete
- 10% loss: 58.05s, 2.05 symbols/sec, complete

Notes:
- These are simulated times at fixed frame cadence; handheld capture will vary.

## How To Verify
- Run `python scripts/demo_assert_complete.py` (expects completion for ~10KB).
- Open the receiver UI and confirm the rank estimate climbs with each accepted symbol and the solve fires as soon as rank reaches k.

## Incremental decoder (follow-up)
The original decoder re-ran a full Gaussian elimination once per bit plane (block_size × 8 = 768 eliminations) on every attempt. Native timings at 15% loss: 10KB 0.55s, 25KB 3.5s, 50KB 26.5s. Pyodide runs on the main thread, so the browser tab froze.

The decoder now stores each symbol as a bitmask row plus one big-integer payload and reduces it against existing pivots as it arrives. One XOR covers every bit plane. The final solve is a back-substitution: 100KB takes ~7ms and 500KB ~0.25s natively. With exact rank, the k+12 margin and timer gating are no longer needed, and the 0%-loss demo now completes in ~48s (previously 53.5s).
