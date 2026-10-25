import { useMemo } from "react";
import { makeQr } from "../lib/qr";
import type { EccLevel } from "../types";

const QUIET_ZONE = 4;

type Props = {
  value: string;
  ecc: EccLevel;
  /** Pin every frame to the same QR version so module size never changes. */
  version: number;
  /** Rendered edge length in CSS pixels. */
  size: number;
};

export const QrCode = ({ value, ecc, version, size }: Props) => {
  const qr = useMemo(() => makeQr(value, ecc, version), [value, ecc, version]);
  const extent = qr.size + QUIET_ZONE * 2;
  return (
    <svg
      className="qr-code"
      width={size}
      height={size}
      viewBox={`${-QUIET_ZONE} ${-QUIET_ZONE} ${extent} ${extent}`}
      shapeRendering="crispEdges"
      role="img"
      aria-label="Tightbeam data frame"
    >
      <rect
        x={-QUIET_ZONE}
        y={-QUIET_ZONE}
        width={extent}
        height={extent}
        fill="#fff"
      />
      <path d={qr.path} fill="#000" />
    </svg>
  );
};
