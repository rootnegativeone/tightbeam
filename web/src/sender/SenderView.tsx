import { useCallback, useEffect, useMemo, useState } from "react";
import { QrCode } from "../components/QrCode";
import {
  encodeTextToBase64,
  formatBytes,
  formatDuration,
  readFileAsBase64,
} from "../lib/format";
import { commonVersion } from "../lib/qr";
import { useWakeLock } from "../lib/wakeLock";
import type { BroadcastPackage, CallPythonJson, EccLevel } from "../types";

const MAX_PAYLOAD_BYTES = 512 * 1024;
const SAMPLE_SIZES = [
  { kb: 0, label: "Short sample (½ KB)" },
  { kb: 10, label: "10 KB" },
  { kb: 100, label: "100 KB" },
  { kb: 500, label: "500 KB" },
] as const;
const BLOCK_SIZES = [
  { value: 224, label: "224 bytes — most data per frame" },
  { value: 160, label: "160 bytes" },
  { value: 96, label: "96 bytes — largest, easiest to scan" },
] as const;
const FRAME_SPEEDS = [
  { value: 300, label: "Fast (3.3 frames/s)" },
  { value: 450, label: "Normal (2.2 frames/s)" },
  { value: 600, label: "Slow (1.7 frames/s)" },
] as const;
const ECC_LEVELS: { value: EccLevel; label: string }[] = [
  { value: "H", label: "H — most robust" },
  { value: "Q", label: "Q" },
  { value: "M", label: "M — bigger modules" },
  { value: "L", label: "L — biggest modules" },
];
const ASSUMED_LOSS = 0.15;

type Source = "sample" | "file" | "paste";
type Phase = "setup" | "preparing" | "sending";

const useStageSize = (boost: number) => {
  const compute = () =>
    Math.round(
      Math.max(
        240,
        Math.min(window.innerHeight - 170, window.innerWidth * 0.55, 720),
      ) * boost,
    );
  const [size, setSize] = useState(compute);
  useEffect(() => {
    const onResize = () => setSize(compute());
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boost]);
  return size;
};

type Props = { call: CallPythonJson };

export const SenderView = ({ call }: Props) => {
  const [phase, setPhase] = useState<Phase>("setup");
  const [source, setSource] = useState<Source>("sample");
  const [sampleKb, setSampleKb] = useState<number>(100);
  const [file, setFile] = useState<File | null>(null);
  const [pasted, setPasted] = useState("");
  const [ecc, setEcc] = useState<EccLevel>("H");
  const [blockSize, setBlockSize] = useState(224);
  const [intervalMs, setIntervalMs] = useState(450);
  const [boost, setBoost] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [broadcast, setBroadcast] = useState<BroadcastPackage | null>(null);
  const [version, setVersion] = useState(1);
  const [frameIndex, setFrameIndex] = useState(0);
  const [loops, setLoops] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [, setTick] = useState(0);
  const stageSize = useStageSize(boost);

  useWakeLock(phase === "sending");

  const payloadSummary = useMemo(() => {
    if (source === "sample") {
      return SAMPLE_SIZES.find((s) => s.kb === sampleKb)?.label ?? "";
    }
    if (source === "file") {
      return file
        ? `${file.name} · ${formatBytes(file.size)}`
        : "No file chosen";
    }
    return pasted
      ? `${formatBytes(new Blob([pasted]).size)} of text`
      : "Nothing pasted";
  }, [source, sampleKb, file, pasted]);

  const start = useCallback(async () => {
    setError(null);
    setPhase("preparing");
    try {
      const settings = [1337, blockSize, ecc, intervalMs] as const;
      let result: any;
      if (source === "sample") {
        result = await call("prepare_broadcast", ...settings, sampleKb);
      } else {
        let base64: string;
        if (source === "file") {
          if (!file) throw new Error("Choose a file to send.");
          if (file.size > MAX_PAYLOAD_BYTES) {
            throw new Error(
              `Files up to ${formatBytes(MAX_PAYLOAD_BYTES)} for now.`,
            );
          }
          base64 = await readFileAsBase64(file);
        } else {
          if (!pasted.trim()) throw new Error("Paste some text to send.");
          if (new Blob([pasted]).size > MAX_PAYLOAD_BYTES) {
            throw new Error(
              `Text up to ${formatBytes(MAX_PAYLOAD_BYTES)} for now.`,
            );
          }
          base64 = encodeTextToBase64(pasted);
        }
        result = await call(
          "prepare_broadcast_from_base64",
          base64,
          ...settings.slice(1),
        );
      }
      if (result?.error) {
        throw new Error(result.error);
      }
      const pkg = result as BroadcastPackage;
      const frames = pkg.frames;
      setVersion(
        commonVersion(
          [frames[0].qr_value, frames[frames.length - 1].qr_value],
          ecc,
        ),
      );
      setBroadcast(pkg);
      setFrameIndex(0);
      setLoops(0);
      setStartedAt(Date.now());
      setPhase("sending");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("setup");
    }
  }, [call, source, sampleKb, file, pasted, ecc, blockSize, intervalMs]);

  const stop = useCallback(() => {
    setPhase("setup");
    setBroadcast(null);
    setStartedAt(null);
  }, []);

  useEffect(() => {
    if (phase !== "sending" || !broadcast) {
      return;
    }
    const count = broadcast.frames.length;
    const timer = window.setInterval(() => {
      setFrameIndex((prev) => {
        if (prev + 1 >= count) {
          setLoops((l) => l + 1);
          return 0;
        }
        return prev + 1;
      });
      setTick((t) => t + 1);
    }, broadcast.metadata.frame_interval_ms);
    return () => window.clearInterval(timer);
  }, [phase, broadcast]);

  const meta = broadcast?.metadata;
  const frame = broadcast?.frames[frameIndex];
  const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
  // Frames a receiver needs at ~15% loss: the sync preamble, then k symbols'
  // worth of rank, plus the interleaved sync frames.
  const typicalSeconds = meta
    ? ((6 + (meta.k / (1 - ASSUMED_LOSS)) * (9 / 8)) * meta.frame_interval_ms) /
      1000
    : null;
  const receiveUrl = `${window.location.origin}/#receive`;

  return (
    <div className="sender">
      <section className="stage" style={{ minHeight: stageSize + 64 }}>
        <div
          className="stage-frame"
          style={{ width: stageSize, height: stageSize }}
        >
          {phase === "sending" && frame && meta ? (
            <QrCode
              value={frame.qr_value}
              ecc={meta.ecc}
              version={version}
              size={stageSize}
            />
          ) : (
            <div className="stage-placeholder">
              {phase === "preparing" ? (
                <p>Encoding…</p>
              ) : (
                <>
                  <QrCode
                    value={receiveUrl}
                    ecc="M"
                    version={commonVersion([receiveUrl], "M")}
                    size={Math.min(220, Math.round(stageSize * 0.42))}
                  />
                  <p>
                    <strong>Scan with your phone's camera</strong> to open the
                    receiver, then press Start sending.
                  </p>
                </>
              )}
            </div>
          )}
        </div>
        <div className="stage-caption">
          {phase === "sending" && broadcast
            ? `Frame ${frameIndex + 1} of ${broadcast.total_frames}${
                loops ? ` · loop ${loops + 1}` : ""
              } · ${formatDuration(elapsed)}`
            : " "}
        </div>
      </section>

      <aside className="panel sender-panel">
        {phase !== "sending" ? (
          <>
            <h2>Send</h2>
            <p className="muted">
              Pick what to send, start, and point a phone at the code.
            </p>

            <div className="field">
              <span className="field-label">What to send</span>
              <div className="segmented" role="tablist">
                {(["sample", "file", "paste"] as const).map((value) => (
                  <button
                    key={value}
                    role="tab"
                    aria-selected={source === value}
                    className={source === value ? "is-active" : ""}
                    onClick={() => setSource(value)}
                  >
                    {value === "sample"
                      ? "POS logs"
                      : value === "file"
                        ? "File"
                        : "Text"}
                  </button>
                ))}
              </div>
              {source === "sample" && (
                <select
                  value={sampleKb}
                  onChange={(e) => setSampleKb(Number(e.target.value))}
                >
                  {SAMPLE_SIZES.map((s) => (
                    <option key={s.kb} value={s.kb}>
                      {s.label}
                    </option>
                  ))}
                </select>
              )}
              {source === "file" && (
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              )}
              {source === "paste" && (
                <textarea
                  rows={5}
                  placeholder="Paste text…"
                  value={pasted}
                  onChange={(e) => setPasted(e.target.value)}
                />
              )}
              <span className="field-hint">{payloadSummary}</span>
            </div>

            <button
              className="button primary large"
              onClick={start}
              disabled={phase === "preparing"}
            >
              {phase === "preparing" ? "Preparing…" : "Start sending"}
            </button>
            {error && <p className="error">{error}</p>}

            <details className="advanced">
              <summary>Advanced</summary>
              <label className="field">
                <span className="field-label">QR error correction</span>
                <select
                  value={ecc}
                  onChange={(e) => setEcc(e.target.value as EccLevel)}
                >
                  {ECC_LEVELS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Data per frame</span>
                <select
                  value={blockSize}
                  onChange={(e) => setBlockSize(Number(e.target.value))}
                >
                  {BLOCK_SIZES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Frame speed</span>
                <select
                  value={intervalMs}
                  onChange={(e) => setIntervalMs(Number(e.target.value))}
                >
                  {FRAME_SPEEDS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="field-hint">
                These settings travel with the transfer, so each receiver test
                report records them automatically.
              </p>
            </details>
          </>
        ) : (
          meta && (
            <>
              <h2>Sending</h2>
              <p className="lede">
                {formatBytes(meta.raw_len)}
                {meta.codec === "deflate" && (
                  <span className="muted">
                    {" "}
                    · compressed to {formatBytes(meta.orig_len)}
                  </span>
                )}
              </p>
              <dl className="facts">
                <div>
                  <dt>Typical phone time</dt>
                  <dd>~{formatDuration(typicalSeconds ?? 0)}</dd>
                </div>
                <div>
                  <dt>Frames per loop</dt>
                  <dd>{broadcast?.total_frames}</dd>
                </div>
                <div>
                  <dt>Settings</dt>
                  <dd>
                    ECC {meta.ecc} · {meta.block_size} B ·{" "}
                    {meta.frame_interval_ms} ms
                  </dd>
                </div>
                <div>
                  <dt>Fingerprint</dt>
                  <dd className="mono">{meta.sha256}</dd>
                </div>
              </dl>
              <p className="muted small">
                On the phone, open <span className="mono">{receiveUrl}</span>{" "}
                and tap Start. The code loops until you stop it, so the phone
                can start at any time.
              </p>
              <label className="field">
                <span className="field-label">Code size</span>
                <input
                  type="range"
                  min="0.7"
                  max="1.2"
                  step="0.05"
                  value={boost}
                  onChange={(e) => setBoost(Number(e.target.value))}
                />
              </label>
              <button className="button large" onClick={stop}>
                Stop
              </button>
            </>
          )
        )}
      </aside>
    </div>
  );
};
