import type { BroadcastMetadata, ReceiverStatus } from "../types";
import type { ScannerInfo } from "./useScanner";

export type Rating = "good" | "ok" | "bad";

export type ReportInput = {
  metadata: BroadcastMetadata | null;
  status: ReceiverStatus | null;
  scanner: ScannerInfo;
  cameraStartedAt: number | null;
  lockedAt: number | null;
  rating: Rating | null;
  note: string;
};

const round = (value: number, digits = 1) =>
  Math.round(value * 10 ** digits) / 10 ** digits;

/** Device hint without the full user agent (which is noisy and fingerprinty). */
const deviceHint = () => {
  const ua = navigator.userAgent;
  const os = /iPhone|iPad/.test(ua)
    ? `iOS ${(ua.match(/OS (\d+)_(\d+)/) ?? []).slice(1).join(".")}`
    : /Android (\d+)/.test(ua)
      ? `Android ${ua.match(/Android (\d+)/)?.[1]}`
      : /Mac OS X/.test(ua)
        ? "macOS"
        : /Windows/.test(ua)
          ? "Windows"
          : "other";
  const browser = /CriOS|Chrome\//.test(ua)
    ? "Chrome"
    : /FxiOS|Firefox\//.test(ua)
      ? "Firefox"
      : /Safari\//.test(ua)
        ? "Safari"
        : "other";
  return {
    os,
    browser,
    screen: `${window.screen.width}×${window.screen.height}`,
  };
};

/**
 * Structured test report for one transfer. Contains settings and measurements
 * only — never payload content.
 */
export const buildReport = ({
  metadata,
  status,
  scanner,
  cameraStartedAt,
  lockedAt,
  rating,
  note,
}: ReportInput) => {
  const result = status?.decode_complete
    ? "verified"
    : status?.phase === "error"
      ? "failed"
      : "incomplete";
  const k = metadata?.k ?? status?.k ?? null;
  return {
    tightbeam_report: 1,
    at: new Date().toISOString(),
    result,
    failure: status?.finalize_error ?? null,
    payload: metadata
      ? {
          raw_bytes: metadata.raw_len,
          wire_bytes: metadata.orig_len,
          codec: metadata.codec,
          k: metadata.k,
        }
      : null,
    sender: metadata
      ? {
          ecc: metadata.ecc,
          block_size: metadata.block_size,
          frame_interval_ms: metadata.frame_interval_ms,
        }
      : null,
    timing_s: {
      camera_to_lock:
        cameraStartedAt && lockedAt
          ? round((lockedAt - cameraStartedAt) / 1000)
          : null,
      receiving: status?.elapsed_s ?? null,
    },
    capture: status
      ? {
          capture_rate: status.capture_rate,
          unique_frames: status.unique_frames,
          frames_expected: status.frames_expected,
          frames_per_block: k ? round(status.unique_frames / k, 2) : null,
          progress: round(status.progress, 3),
          duplicates: status.duplicate_frames,
          rejected: status.rejected,
        }
      : null,
    device: {
      ...deviceHint(),
      decoder: scanner.decoder,
      camera: scanner.facing,
      video: scanner.resolution,
    },
    rating,
    note: note.trim() || null,
  };
};

export type Report = ReturnType<typeof buildReport>;

/** One-line, human-readable version of the report. */
export const summarizeReport = (report: Report) => {
  const parts: string[] = [];
  if (report.payload) {
    parts.push(`${Math.round(report.payload.raw_bytes / 1024)} KB`);
  }
  if (report.timing_s.receiving !== null) {
    parts.push(`${report.timing_s.receiving.toFixed(1)} s receiving`);
  }
  if (report.capture?.capture_rate != null) {
    parts.push(
      `${Math.round(report.capture.capture_rate * 100)}% of frames caught`,
    );
  }
  if (report.sender) {
    parts.push(
      `ECC ${report.sender.ecc}, ${report.sender.block_size} B blocks`,
    );
  }
  return `${report.result.toUpperCase()} · ${parts.join(" · ")}`;
};
