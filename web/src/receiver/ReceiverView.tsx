import { useCallback, useMemo, useRef, useState } from "react";
import { BlockGrid } from "../components/BlockGrid";
import { formatBytes, formatDuration, formatEta } from "../lib/format";
import { useWakeLock } from "../lib/wakeLock";
import type { CallPythonJson } from "../types";
import { buildReport, summarizeReport, type Rating } from "./report";
import { useScanner } from "./useScanner";
import { useTransfer, type RecoveredPayload } from "./useTransfer";

type CopyState = "idle" | "copied" | "failed";

const useCopy = () => {
  const [state, setState] = useState<CopyState>("idle");
  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    window.setTimeout(() => setState("idle"), 1800);
  }, []);
  return { state, copy };
};

const payloadFile = (payload: RecoveredPayload, sessionId: string) => {
  if (!payload.isBase64) {
    return new File([payload.text], `tightbeam-${sessionId}.txt`, {
      type: "text/plain",
    });
  }
  const binary = atob(payload.text);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return new File([bytes], `tightbeam-${sessionId}.bin`, {
    type: "application/octet-stream",
  });
};

const savePayload = async (payload: RecoveredPayload, sessionId: string) => {
  const file = payloadFile(payload, sessionId);
  // iOS: the share sheet offers "Save to Files", AirDrop, Mail, etc.
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: file.name });
      return;
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
    }
  }
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};

type Props = { call: CallPythonJson };

export const ReceiverView = ({ call }: Props) => {
  const [cameraStartedAt, setCameraStartedAt] = useState<number | null>(null);
  const [rating, setRating] = useState<Rating | null>(null);
  const [note, setNote] = useState("");
  const reportCopy = useCopy();
  const payloadCopy = useCopy();

  // The scanner and the transfer reference each other: completion stops the
  // camera, and every scanned value goes to the transfer.
  const stopCameraRef = useRef<() => void>(() => undefined);
  const transfer = useTransfer(call, () => stopCameraRef.current());
  const scanner = useScanner(transfer.handleValue);
  stopCameraRef.current = scanner.stop;

  const { lock, metadata, status, payload } = transfer;
  const running = scanner.state === "running" || scanner.state === "starting";
  const done = Boolean(status?.decode_complete);
  const failed = status?.phase === "error";
  const hadSession = Boolean(metadata);
  useWakeLock(running);

  const start = () => {
    transfer.reset();
    setRating(null);
    setNote("");
    setCameraStartedAt(Date.now());
    void scanner.start();
  };

  const report = useMemo(
    () =>
      buildReport({
        metadata,
        status,
        scanner: scanner.info,
        cameraStartedAt,
        lockedAt: transfer.lockedAt,
        rating,
        note,
      }),
    [
      metadata,
      status,
      scanner.info,
      cameraStartedAt,
      transfer.lockedAt,
      rating,
      note,
    ],
  );

  const stage:
    "idle" | "searching" | "locking" | "receiving" | "done" | "failed" = done
    ? "done"
    : failed
      ? "failed"
      : !running
        ? "idle"
        : lock.state === "locked"
          ? "receiving"
          : lock.state === "acquiring"
            ? hadSession
              ? "receiving"
              : "locking"
            : "searching";

  const instruction = {
    idle: hadSession ? "Paused" : "",
    searching: "Point at the code on the sending screen",
    locking: `Locking on… ${lock.progress}/${lock.target}`,
    receiving:
      lock.state === "locked"
        ? "Hold steady"
        : "Lost the code — point back at the screen",
    done: "",
    failed: "",
  }[stage];

  const percent = Math.floor((status?.progress ?? 0) * 100);

  return (
    <div className="receiver">
      <section className={`viewfinder is-${stage}`}>
        <video ref={scanner.videoRef} playsInline muted autoPlay />
        <div className="reticle" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        {stage !== "idle" && stage !== "done" && stage !== "failed" && (
          <button
            className="icon-button flip"
            onClick={scanner.flip}
            aria-label="Switch camera"
          >
            ⟲
          </button>
        )}
        {stage === "idle" && (
          <div className="viewfinder-center">
            <button className="button primary large" onClick={start}>
              {hadSession ? "Resume" : "Start receiving"}
            </button>
            {scanner.error && <p className="error on-dark">{scanner.error}</p>}
          </div>
        )}
        {stage === "done" && (
          <div className="viewfinder-center">
            <div className="check" aria-hidden="true">
              ✓
            </div>
            <p className="viewfinder-title">Received &amp; verified</p>
          </div>
        )}
        {stage === "failed" && (
          <div className="viewfinder-center">
            <div className="check is-failed" aria-hidden="true">
              !
            </div>
            <p className="viewfinder-title">Integrity check failed</p>
          </div>
        )}
        <div className="viewfinder-instruction">{instruction || " "}</div>
      </section>

      <section className="panel progress-panel">
        {done && metadata ? (
          <>
            <h2>
              {formatBytes(metadata.raw_len)} in{" "}
              {formatDuration(status?.elapsed_s ?? 0)}
            </h2>
            <p className="muted">
              Fingerprint verified (SHA-256{" "}
              <span className="mono">{metadata.sha256}</span>)
              {status?.capture_rate != null &&
                ` · caught ${Math.round(status.capture_rate * 100)}% of frames`}
            </p>
            {status && <BlockGrid blocks={status.blocks} />}
            <div className="actions">
              <button
                className="button primary"
                onClick={() =>
                  payload && savePayload(payload, metadata.session_id)
                }
                disabled={!payload}
              >
                Save or share
              </button>
              <button
                className="button"
                onClick={() => payload && payloadCopy.copy(payload.text)}
                disabled={!payload}
              >
                {payloadCopy.state === "copied" ? "Copied" : "Copy"}
              </button>
              <button className="button" onClick={start}>
                Receive another
              </button>
            </div>
            {payload && (
              <details className="payload">
                <summary>
                  View contents{payload.isBase64 ? " (binary, base64)" : ""}
                </summary>
                <pre>{payload.text.slice(0, 20000)}</pre>
                {payload.text.length > 20000 && (
                  <p className="muted small">
                    Showing the first 20,000 characters.
                  </p>
                )}
              </details>
            )}
          </>
        ) : failed ? (
          <>
            <h2>Something didn't add up</h2>
            <p className="muted">
              All the data arrived, but it didn't match the sender's fingerprint
              {status?.finalize_error ? ` (${status.finalize_error})` : ""}.
              Nothing was saved. Start the sender again and retry.
            </p>
            <button className="button primary" onClick={start}>
              Try again
            </button>
          </>
        ) : hadSession && status ? (
          <>
            <div className="progress-figure">
              <span className="percent">{percent}%</span>
              <span className="muted">
                {transfer.etaSeconds !== null
                  ? formatEta(transfer.etaSeconds)
                  : "receiving…"}
                {metadata && ` · ${formatBytes(metadata.raw_len)}`}
              </span>
            </div>
            <div className="progress-bar">
              <div style={{ transform: `scaleX(${status.progress})` }} />
            </div>
            <BlockGrid blocks={status.blocks} />
            <p className="legend">
              <span className="swatch is-direct" /> caught directly
              <span className="swatch is-repaired" /> rebuilt from repair frames
            </p>
            {running ? (
              <button className="button subtle" onClick={scanner.stop}>
                Pause
              </button>
            ) : null}
          </>
        ) : (
          <>
            <h2>Receive</h2>
            <ol className="steps">
              <li>
                On the computer, open Tightbeam and choose <strong>Send</strong>
                .
              </li>
              <li>
                Tap <strong>Start receiving</strong> and allow the camera.
              </li>
              <li>
                Point this phone at the code. Missed frames are fine — keep it
                roughly steady.
              </li>
            </ol>
            {running && (
              <button className="button subtle" onClick={scanner.stop}>
                Cancel
              </button>
            )}
          </>
        )}
      </section>

      {hadSession && (done || failed || !running) && (
        <section className="panel report-panel">
          <h3>Test report</h3>
          <p className="muted small">{summarizeReport(report)}</p>
          <div className="rating" role="group" aria-label="How did it go?">
            {(
              [
                ["good", "😀", "Smooth"],
                ["ok", "😐", "Okay"],
                ["bad", "😞", "Rough"],
              ] as const
            ).map(([value, emoji, label]) => (
              <button
                key={value}
                className={rating === value ? "is-active" : ""}
                onClick={() => setRating(rating === value ? null : value)}
              >
                <span aria-hidden="true">{emoji}</span> {label}
              </button>
            ))}
          </div>
          <input
            className="note"
            placeholder="Notes: distance, lighting, glare…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            className="button primary"
            onClick={() =>
              reportCopy.copy(
                `${summarizeReport(report)}\n${JSON.stringify(report)}`,
              )
            }
          >
            {reportCopy.state === "copied"
              ? "Report copied"
              : reportCopy.state === "failed"
                ? "Copy failed"
                : "Copy report"}
          </button>
          <p className="muted small">
            Paste it into a message or GitHub issue. It contains settings and
            timings only, never the data you received.
          </p>
        </section>
      )}

      <details className="panel diagnostics">
        <summary>Diagnostics</summary>
        <dl className="facts">
          <div>
            <dt>Decoder</dt>
            <dd>
              {scanner.info.decoder === "native"
                ? "BarcodeDetector (built in)"
                : "zxing-cpp (WebAssembly)"}
            </dd>
          </div>
          <div>
            <dt>Camera</dt>
            <dd>
              {scanner.info.facing === "environment" ? "rear" : "front"}
              {scanner.info.resolution ? ` · ${scanner.info.resolution}` : ""}
            </dd>
          </div>
          <div>
            <dt>Codes read</dt>
            <dd>{scanner.info.detections}</dd>
          </div>
          <div>
            <dt>Lock</dt>
            <dd>
              {lock.state}{" "}
              {lock.state !== "locked" && `${lock.progress}/${lock.target}`}
            </dd>
          </div>
          {status && (
            <>
              <div>
                <dt>Rank</dt>
                <dd>
                  {status.rank} / {status.k}
                </dd>
              </div>
              <div>
                <dt>Frames</dt>
                <dd>
                  {status.unique_frames} unique · {status.duplicate_frames}{" "}
                  repeats · {status.redundant_symbols} redundant
                </dd>
              </div>
              <div>
                <dt>Rejected</dt>
                <dd>
                  {Object.entries(status.rejected)
                    .map(([reason, n]) => `${reason} ${n}`)
                    .join(", ") || "none"}
                </dd>
              </div>
            </>
          )}
          {metadata && (
            <div>
              <dt>Session</dt>
              <dd className="mono">
                {metadata.session_id} · ECC {metadata.ecc} ·{" "}
                {metadata.block_size} B · {metadata.frame_interval_ms} ms
              </dd>
            </div>
          )}
          {transfer.error && (
            <div>
              <dt>Error</dt>
              <dd>{transfer.error}</dd>
            </div>
          )}
        </dl>
      </details>
    </div>
  );
};
