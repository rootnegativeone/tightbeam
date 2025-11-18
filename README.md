# Tightbeam

Tightbeam is a burst-erasure-resilient, air-gapped data transfer system using QR-GIFs. It allows secure one-way exfiltration from devices with a display to those with a camera, even in high-loss environments.

## System Summary

- **Encoder**: On-device SDK generates fountain-encoded QR-GIFs.
- **Decoder**: Camera-equipped device captures the stream and reconstructs the original data.
- **Use Case**: Secure logs or telemetry retrieval from air-gapped or access-controlled systems.

## Components

- `common/`: Shared fountain code primitives, metrics, and utilities.
- `decoder/`: Python receiver-side rebuild helpers.
- `demo/`: Standalone scripts for generating QR bursts from sample data.
- `web/`: Vite + React simulation (sender + receiver UIs) loading the Python stack through Pyodide.
- `tests/`: Unit and integration coverage.
- `logs/`: Generated telemetry during local experiments.

## Goals

- Avoid decoding plateaus using fountain codes and interleaving.
- Operate in highly lossy optical links (e.g., burst losses, frame blur).
- Maintain userless, handshake-free operation.

## Web Simulation

The `web` directory ships a self-contained sender/receiver demo that runs the real Python encoder/decoder entirely in the browser via Pyodide. It is the fastest way to iterate on UX, test iPhone capture, and produce Vercel-ready builds.

### Prerequisites

```bash
cd web
npm install
```

### Local development

```bash
npm run dev
```

Open the printed URL (default `http://localhost:5173`). The hero screen lets you choose between **Sender Console** and **Receiver Console**.

#### Sender Console

- By default the QR renderer uses a high-contrast profile (black modules on a white background) with error-correction level **H** and a quiet zone, which has proven the most reliable on iPhone Safari.
- Use the **“Use brand palette”** checkbox to flip back to the mint-on-navy styling once you have lock stability.
- The **Single-frame Test** panel can pin a metadata/sync/symbol frame for manual capture or copy its payload onto the clipboard (helpful when debugging with static codes).
- `Auto loop bursts` and the size slider let you tune cadence and apparent QR size without touching code.

#### Receiver Console

- Tap **Start Receiving** to request camera access. The UI shows the active camera, decoder mode (native BarcodeDetector vs ZXing fallback), observed video resolution, detection cadence, and luminance estimates.
- The **Snapshot Decode** button freezes the current frame to a hidden canvas and forces a decode. Use this when you want to validate a static QR before attempting burst playback.
- Coverage remains cumulative: once metadata is applied it stays in memory even if the lock indicator reverts to “acquiring” after a short dropout.
- Sync lock now requires only two confirmation frames, and the inactivity timeout is ~4.5 s—gentle camera motion should not zero coverage.
- The guidance panel has a fixed height to prevent “wiggling” when messages change.

### Building for deployment

```bash
npm run build
```

Vercel deployments use the Vite production output under `web/dist`.

### Mobile capture checklist

1. Start in the high-contrast palette and position the phone so the QR nearly fills the reticle.
2. Watch the diagnostics: if **Detections** stays at 0, increase brightness or move closer; if cadence registers but the payload never completes, hold steady until coverage reaches 100 %.
3. Use **Snapshot Decode** on a pinned single frame to confirm the phone can read the code when motion is removed.
4. Once stable, toggle **Use brand palette** if you need branded visuals—the fallback decoder may require larger QR sizes or brighter screens when colours change.

## Testing

- `npm run build` in `web/` — validates the React + Pyodide bundle.
- Python unit tests live under `tests/` and can be executed with `pytest`.

## Status

Sprint 1: baseline encode/decode pipeline, interactive demo, and mobile capture hardening. Further work is tracking in issues for improved native decoders and production packaging.
