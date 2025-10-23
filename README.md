# Tightbeam

Tightbeam is a burst-erasure-resilient, air-gapped data transfer system using QR-GIFs. It allows secure one-way exfiltration from devices with a display to those with a camera, even in high-loss environments.

## System Summary

- **Encoder**: On-device SDK generates fountain-encoded QR-GIFs.
- **Decoder**: Camera-equipped device captures the stream and reconstructs the original data.
- **Use Case**: Secure logs or telemetry retrieval from air-gapped or access-controlled systems.

## Components

- `encoder/`: QR-GIF generator and fountain encoder.
- `decoder/`: Camera capture and fountain decoder.
- `utilities/`: Shared utilities (e.g. frame indexer, metrics logger).
- `tests/`: Unit and integration tests.
- `logs/`: Log files.
- `web/`: Vite + React simulation that wraps the Python encoder/decoder via Pyodide.

## Goals

- Avoid decoding plateaus using fountain codes and interleaving.
- Operate in highly lossy optical links (e.g., burst losses, frame blur).
- Maintain userless, handshake-free operation.

## Status

Sprint 1 in progress: baseline encoder and decoder.

## Web Simulation

The `web` folder hosts a self-contained browser demo that exercises the Python LT
encoder/decoder end to end. It embeds the Tightbeam modules in Pyodide so the
Send → Encode → Receive flow runs client-side without a backend.

```bash
cd web
npm install
npm run dev
```

Open the printed URL (defaults to http://localhost:5173) and click **Send Logs** to
watch QR bursts stream, lose frames in a simulated burst channel, and get rebuilt
by the decoder. The UI surfaces coverage, metrics, and the reconstructed payload
for easy recording and Vercel deployment.
