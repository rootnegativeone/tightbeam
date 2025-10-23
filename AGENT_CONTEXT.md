pyenv install 3.12.3# Tightbeam Agent Context

You are helping develop Tightbeam, a system for burst-erasure-resistant, air-gapped data transfer using QR-GIFs.

## Priorities

- Use Python for encoder and decoder components.
- Prioritize resilience to burst loss (Gilbert-Elliott-style channel).
- Prefer rateless fountain codes.
- Use testable, modular structure.
- Metrics-driven development (time to decode, index coverage, etc.).
- Visual UX isn't important yet — focus on core transfer mechanism.

## Layout

- `encoder/`: chunks data, encodes as QR-GIF.
- `decoder/`: camera input, frame decoding, reconstruction.
- `utilities/`: CRCs, frame sequence logic, metrics.
- `tests/`: Unit and integration tests.
- `logs/`: Log files
