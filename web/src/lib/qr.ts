import QRCode from "qrcode";
import type { EccLevel } from "../types";

export type QrMatrix = { size: number; version: number; path: string };

/**
 * Encode ``text`` at a fixed ECC level (no automatic ECC boosting, so the
 * selected level is what the camera actually gets). Pass ``version`` to pin
 * the symbol size.
 */
export const makeQr = (
  text: string,
  ecc: EccLevel,
  version?: number,
): QrMatrix => {
  const qr = QRCode.create(text, { errorCorrectionLevel: ecc, version });
  const { size, data } = qr.modules;
  // One SVG path with a 1x1 square per dark module; rows are merged into runs
  // to keep the path short.
  let path = "";
  for (let row = 0; row < size; row += 1) {
    let col = 0;
    while (col < size) {
      if (!data[row * size + col]) {
        col += 1;
        continue;
      }
      const start = col;
      while (col < size && data[row * size + col]) {
        col += 1;
      }
      path += `M${start} ${row}h${col - start}v1h${start - col}z`;
    }
  }
  return { size, version: qr.version, path };
};

/** Smallest QR version that fits every one of ``values`` at ``ecc``. */
export const commonVersion = (values: string[], ecc: EccLevel) =>
  values.reduce((max, value) => Math.max(max, makeQr(value, ecc).version), 1);
