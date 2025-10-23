import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { ensurePyodide } from "./lib/pyodide";
import "./App.css";

type PyodideStatus = "idle" | "loading" | "ready" | "error";
type Role = "none" | "sender" | "receiver";
type PlaybackState = "idle" | "playing" | "finished";

type BroadcastMetadata = {
  block_size: number;
  k: number;
  orig_len: number;
  integrity_check: boolean;
};

type BroadcastFrameMeta = {
  sequence: number;
  type: "meta";
  content: BroadcastMetadata;
  qr_value: string;
};

type BroadcastFrameSymbol = {
  sequence: number;
  type: "symbol";
  indices: number[];
  degree: number;
  payload_hex: string;
  systematic: boolean;
  qr_value: string;
};

type BroadcastFrame = BroadcastFrameMeta | BroadcastFrameSymbol;

type BroadcastPackage = {
  seed: number;
  payload_text: string;
  metadata: BroadcastMetadata;
  frames: BroadcastFrame[];
  total_frames: number;
  systematic_count: number;
  redundant_count: number;
};

type MetricsSummary = {
  total_symbols: number;
  degree_hist: Record<string, number>;
  average_degree: number;
  decode_attempts: number;
  decode_success_rate: number;
  average_decode_duration: number;
  average_symbols_used: number;
  rejected_symbols: Record<string, number>;
};

type ReceiverStatus = {
  redundant: boolean;
  newly_added: boolean;
  symbols_observed: number;
  unique_symbols: number;
  coverage: number;
  decode_complete: boolean;
  recovered_text: string | null;
  metrics: MetricsSummary;
};

type CallPythonJson = (fnName: string, ...args: unknown[]) => Promise<any>;

type SenderViewProps = {
  callPythonJson: CallPythonJson;
  onBack: () => void;
};

type ReceiverViewProps = {
  callPythonJson: CallPythonJson;
  onBack: () => void;
};

type BarcodeDetection = {
  rawValue: string;
};

type BarcodeDetectorLike = {
  detect: (source: CanvasImageSource) => Promise<BarcodeDetection[]>;
};

type BarcodeDetectorCtor = new (options?: {
  formats?: string[];
}) => BarcodeDetectorLike;

type ZXingReader = {
  decodeFromVideoDevice: (
    deviceId: string | undefined,
    videoElement: HTMLVideoElement,
    callback: (result: { getText(): string } | null, err: unknown) => void,
  ) => Promise<void>;
  reset: () => void;
};

type ZXingNotFound = new (...args: any[]) => Error;

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

const describeGuidance = (
  status: ReceiverStatus | null,
  metadata: BroadcastMetadata | null,
) => {
  if (!metadata) {
    return "Start with the metadata frame — hover over the first QR at the sender.";
  }
  if (!status) {
    return "Align the terminal screen inside the guide and hold steady.";
  }
  if (status.decode_complete) {
    return "Transfer complete. Share the reconstructed payload.";
  }
  if (status.coverage < 0.3) {
    return "Move a little closer and keep the screen centered.";
  }
  if (status.coverage < 0.65) {
    return "Great capture — hold position while the next bursts arrive.";
  }
  return "Almost there. Keep the QR in view for the final frames.";
};

const SenderView = ({ callPythonJson, onBack }: SenderViewProps) => {
  const [isPreparing, setIsPreparing] = useState(false);
  const [broadcast, setBroadcast] = useState<BroadcastPackage | null>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>("idle");
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const playbackTimer = useRef<number | null>(null);

  const frames = broadcast?.frames ?? [];
  const currentFrame = frames[currentFrameIndex];
  const totalFrames = broadcast?.total_frames ?? 0;

  const handlePrepare = useCallback(async () => {
    setIsPreparing(true);
    setError(null);
    try {
      const result = await callPythonJson("prepare_broadcast");
      setBroadcast(result as BroadcastPackage);
      setPlaybackState("idle");
      setCurrentFrameIndex(0);
    } catch (err) {
      console.error(err);
      setError("Unable to prepare broadcast. Retry in a moment.");
    } finally {
      setIsPreparing(false);
    }
  }, [callPythonJson]);

  const stopPlaybackTimer = useCallback(() => {
    if (playbackTimer.current !== null) {
      window.clearInterval(playbackTimer.current);
      playbackTimer.current = null;
    }
  }, []);

  const handleStartBurst = useCallback(() => {
    if (!broadcast) {
      return;
    }
    stopPlaybackTimer();
    setCurrentFrameIndex(0);
    setPlaybackState("playing");
  }, [broadcast, stopPlaybackTimer]);

  const handlePause = useCallback(() => {
    stopPlaybackTimer();
    setPlaybackState("idle");
  }, [stopPlaybackTimer]);

  useEffect(() => {
    if (!broadcast || playbackState !== "playing") {
      return;
    }
    stopPlaybackTimer();
    const framesCount = broadcast.frames.length;
    let idx = 0;
    setCurrentFrameIndex(0);

    const timer = window.setInterval(() => {
      idx += 1;
      if (idx >= framesCount) {
        stopPlaybackTimer();
        setPlaybackState("finished");
        return;
      }
      setCurrentFrameIndex(idx);
    }, 650);

    playbackTimer.current = timer;

    return () => {
      window.clearInterval(timer);
      playbackTimer.current = null;
    };
  }, [broadcast, playbackState, stopPlaybackTimer]);

  useEffect(() => () => stopPlaybackTimer(), [stopPlaybackTimer]);

  const frameLabel = useMemo(() => {
    if (!currentFrame) {
      return "Ready";
    }
    if (currentFrame.type === "meta") {
      return "Metadata";
    }
    return currentFrame.systematic ? "Systematic Frame" : "Redundant Frame";
  }, [currentFrame]);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Sender Console</h2>
        <div className="panel-actions">
          <button className="link" onClick={onBack}>
            Switch Role
          </button>
        </div>
      </div>
      <div className="panel-body">
        <div className="sender-grid">
          <div className="qr-stage">
            {currentFrame ? (
              <QRCodeSVG
                value={currentFrame.qr_value}
                size={260}
                bgColor="#07130d"
                fgColor="#d5ffe7"
              />
            ) : (
              <div className="placeholder">Prepare broadcast</div>
            )}
            <div className="frame-meta">
              <div>
                {currentFrame
                  ? `Frame ${currentFrameIndex + 1} of ${totalFrames}`
                  : "Idle"}
              </div>
              <div>{frameLabel}</div>
              {currentFrame?.type === "symbol" && (
                <div>
                  d{currentFrame.degree} · {currentFrame.indices.join(", ")}
                </div>
              )}
              {currentFrame?.type === "meta" && broadcast && (
                <div>
                  Block {broadcast.metadata.block_size} · k=
                  {broadcast.metadata.k}
                </div>
              )}
            </div>
          </div>

          <div className="sender-controls">
            <div className="control-strip">
              <button
                className="action"
                onClick={handlePrepare}
                disabled={isPreparing}
              >
                {isPreparing ? "Preparing…" : "Prepare Broadcast"}
              </button>
              <button
                className="action secondary"
                onClick={
                  playbackState === "playing" ? handlePause : handleStartBurst
                }
                disabled={!broadcast}
              >
                {playbackState === "playing"
                  ? "Pause"
                  : playbackState === "finished"
                    ? "Replay"
                    : "Start Burst"}
              </button>
            </div>

            {broadcast && (
              <div className="stats">
                <h3>Transmission Stats</h3>
                <ul>
                  <li>
                    Frames: {broadcast.total_frames} (
                    {broadcast.systematic_count} systematic +{" "}
                    {broadcast.redundant_count} redundant)
                  </li>
                  <li>Block size: {broadcast.metadata.block_size} bytes</li>
                  <li>Source blocks (k): {broadcast.metadata.k}</li>
                </ul>
                <details>
                  <summary>Payload preview</summary>
                  <pre>{broadcast.payload_text}</pre>
                </details>
              </div>
            )}

            {error && <div className="error-text">{error}</div>}
          </div>
        </div>
      </div>
    </section>
  );
};

const ReceiverView = ({ callPythonJson, onBack }: ReceiverViewProps) => {
  const [metadata, setMetadata] = useState<BroadcastMetadata | null>(null);
  const [status, setStatus] = useState<ReceiverStatus | null>(null);
  const [guidance, setGuidance] = useState<string>(
    "Invite the sender to start the burst, then scan the first QR.",
  );
  const [cameraState, setCameraState] = useState<
    "idle" | "starting" | "running" | "error"
  >("idle");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [scannerSupported, setScannerSupported] = useState<boolean | null>(
    null,
  );
  const [useFallbackScanner, setUseFallbackScanner] = useState(false);
  const [lastFrame, setLastFrame] = useState<string | null>(null);
  const lastValueRef = useRef<string | null>(null);
  const animationRef = useRef<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<BarcodeDetectorLike | null>(null);
  const fallbackReaderRef = useRef<ZXingReader | null>(null);
  const fallbackNotFoundRef = useRef<ZXingNotFound | null>(null);

  useEffect(() => {
    const Detector = (
      window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }
    ).BarcodeDetector;
    if (Detector) {
      detectorRef.current = new Detector({ formats: ["qr_code"] });
      setScannerSupported(true);
    } else {
      import("@zxing/browser")
        .then((module) => {
          fallbackReaderRef.current = new module.BrowserQRCodeReader();
          fallbackNotFoundRef.current = module.NotFoundException;
          setUseFallbackScanner(true);
          setScannerSupported(true);
        })
        .catch((err) => {
          console.error("ZXing fallback unavailable", err);
          setScannerSupported(false);
        });
    }
  }, []);

  useEffect(() => {
    setGuidance(describeGuidance(status, metadata));
  }, [status, metadata]);

  const stopCamera = useCallback(() => {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (useFallbackScanner && fallbackReaderRef.current) {
      try {
        fallbackReaderRef.current.reset();
      } catch (err) {
        console.warn("Fallback reader reset failed", err);
      }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraState("idle");
  }, [useFallbackScanner]);

  useEffect(() => () => stopCamera(), [stopCamera]);

  const handleMetadata = useCallback(
    async (meta: BroadcastMetadata) => {
      const result = await callPythonJson(
        "reset_receiver",
        meta.block_size,
        meta.k,
        meta.orig_len,
        meta.integrity_check,
      );
      if (result.error) {
        throw new Error(result.error);
      }
      setMetadata(meta);
      setStatus(null);
    },
    [callPythonJson],
  );

  const handleSymbol = useCallback(
    async (sequence: number, indices: number[], payloadHex: string) => {
      const result = await callPythonJson(
        "receiver_add_symbol",
        sequence,
        indices,
        payloadHex,
      );
      if (result.error) {
        throw new Error(result.error);
      }
      setStatus(result as ReceiverStatus);
    },
    [callPythonJson],
  );

  const processValue = useCallback(
    async (value: string) => {
      if (value === lastValueRef.current) {
        return;
      }
      lastValueRef.current = value;
      setLastFrame(value);

      if (value.startsWith("M:")) {
        const payload = value.slice(2);
        const meta = JSON.parse(payload) as BroadcastMetadata;
        await handleMetadata(meta);
        return;
      }

      if (!value.startsWith("S:")) {
        return;
      }
      const remainder = value.slice(2);
      const [sequencePart, indicesPart, payloadHex] = remainder.split("|", 3);
      if (!sequencePart || !indicesPart || !payloadHex) {
        return;
      }
      const sequence = Number.parseInt(sequencePart, 10);
      if (Number.isNaN(sequence)) {
        return;
      }
      const indices = indicesPart
        .split(",")
        .filter(Boolean)
        .map((item) => Number.parseInt(item, 10))
        .filter((item) => !Number.isNaN(item));
      if (!indices.length) {
        return;
      }
      await handleSymbol(sequence, indices, payloadHex);
    },
    [handleMetadata, handleSymbol],
  );

  const scanLoop = useCallback(async () => {
    if (useFallbackScanner) {
      return;
    }
    if (!detectorRef.current || !videoRef.current) {
      return;
    }
    try {
      const detections = await detectorRef.current.detect(videoRef.current);
      if (detections.length > 0) {
        const { rawValue } = detections[0];
        if (rawValue) {
          await processValue(rawValue);
        }
      }
    } catch (err) {
      console.error(err);
      setCameraError("Scanner interrupted. Refresh to retry.");
      stopCamera();
      return;
    }
    animationRef.current = requestAnimationFrame(scanLoop);
  }, [processValue, stopCamera, useFallbackScanner]);

  const startCamera = useCallback(async () => {
    setCameraError(null);
    if (scannerSupported === false) {
      setCameraError("QR detection unavailable in this browser.");
      return;
    }
    try {
      setCameraState("starting");
      lastValueRef.current = null;
      setMetadata(null);
      setStatus(null);
      if (useFallbackScanner) {
        const reader = fallbackReaderRef.current;
        const video = videoRef.current;
        if (!reader || !video) {
          throw new Error("Fallback scanner unavailable");
        }
        await reader.decodeFromVideoDevice(
          undefined,
          video,
          async (result, err) => {
            if (result) {
              const text = result.getText();
              if (text) {
                await processValue(text);
              }
            } else if (
              err &&
              fallbackNotFoundRef.current &&
              !(err instanceof fallbackNotFoundRef.current)
            ) {
              console.warn("Fallback scanner error", err);
            }
          },
        );
        setCameraState("running");
      } else {
        if (!detectorRef.current) {
          setCameraError("QR detection unavailable in this browser.");
          setCameraState("error");
          return;
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) {
          throw new Error("Video element unavailable");
        }
        video.srcObject = stream;
        await video.play();
        setCameraState("running");
        animationRef.current = requestAnimationFrame(scanLoop);
      }
    } catch (err) {
      console.error(err);
      setCameraState("error");
      setCameraError("Camera permission denied or unavailable.");
    }
  }, [scanLoop, scannerSupported, useFallbackScanner, processValue]);

  const coveragePercent = status ? formatPercent(status.coverage) : "0.0%";

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Receiver Console</h2>
        <div className="panel-actions">
          <button className="link" onClick={onBack}>
            Switch Role
          </button>
        </div>
      </div>
      <div className="panel-body">
        <div className="receiver-grid">
          <div className="guidance">
            <h3>Guidance</h3>
            <p>{guidance}</p>
            <div className="control-strip">
              <button
                className="action"
                onClick={startCamera}
                disabled={
                  cameraState === "starting" || cameraState === "running"
                }
              >
                {cameraState === "running"
                  ? "Scanning"
                  : cameraState === "starting"
                    ? "Starting…"
                    : "Start Receiving"}
              </button>
              <button className="action secondary" onClick={stopCamera}>
                Stop
              </button>
            </div>
            {cameraError && <div className="error-text">{cameraError}</div>}
            <div className="progress">
              <div className="progress-label">
                Coverage &nbsp;{coveragePercent}
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min(status?.coverage ?? 0, 1) * 100}%`,
                  }}
                />
              </div>
            </div>
            {status && (
              <ul className="metrics-list">
                <li>Symbols observed: {status.symbols_observed}</li>
                <li>Unique indices: {status.unique_symbols}</li>
                <li>
                  Decode status:{" "}
                  {status.decode_complete ? "Recovered" : "In progress"}
                </li>
              </ul>
            )}
          </div>

          <div className="capture-stage">
            <div className="capture-outline">
              <div className="capture-text">
                {metadata
                  ? "Hold the QR burst in this frame"
                  : "Awaiting metadata frame"}
              </div>
            </div>
            <div className="capture-footer">
              <div className="capture-status">
                {lastFrame
                  ? `Last capture: ${lastFrame.slice(0, 48)}…`
                  : "No frames yet"}
              </div>
              {status?.recovered_text && (
                <details>
                  <summary>Reconstructed payload</summary>
                  <pre>{status.recovered_text}</pre>
                </details>
              )}
            </div>
          </div>
        </div>
        <video ref={videoRef} className="hidden-video" playsInline muted />
      </div>
    </section>
  );
};

export default function App() {
  const [pyodideStatus, setPyodideStatus] = useState<PyodideStatus>("idle");
  const [pyodideError, setPyodideError] = useState<string | null>(null);
  const [role, setRole] = useState<Role>("none");

  useEffect(() => {
    let cancelled = false;
    setPyodideStatus("loading");
    ensurePyodide()
      .then(() => {
        if (!cancelled) {
          setPyodideStatus("ready");
        }
      })
      .catch((err: unknown) => {
        console.error(err);
        if (!cancelled) {
          setPyodideError(err instanceof Error ? err.message : String(err));
          setPyodideStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const callPythonJson = useCallback<CallPythonJson>(
    async (fnName, ...args) => {
      const pyodide = await ensurePyodide();
      const fn = pyodide.globals.get(fnName);
      try {
        const result = fn(...args);
        const text = typeof result === "string" ? result : result.toString();
        if (result && typeof result === "object" && "destroy" in result) {
          (result as unknown as { destroy: () => void }).destroy();
        }
        return JSON.parse(text);
      } finally {
        fn.destroy();
      }
    },
    [],
  );

  return (
    <div className="app-shell">
      <header className="hero">
        <h1>Tightbeam Optical Transfer</h1>
        <p>
          Run a live air-gapped demo. One screen emits QR bursts just like a POS
          terminal, another device locks onto them and reconstructs the payload
          in real time.
        </p>
        <div className="status-row">
          <span className={`status-pill status-${pyodideStatus}`}>
            Pyodide {pyodideStatus === "ready" ? "ready" : pyodideStatus}
          </span>
          {pyodideError && <span className="error-text">{pyodideError}</span>}
        </div>
        {role === "none" && (
          <div className="role-actions">
            <button
              className="role-card"
              onClick={() => setRole("sender")}
              disabled={pyodideStatus !== "ready"}
            >
              <h3>Sender Console</h3>
              <p>
                Animate QR bursts in a Clover-style POS bezel. Perfect for the
                laptop driving the display.
              </p>
            </button>
            <button
              className="role-card"
              onClick={() => setRole("receiver")}
              disabled={pyodideStatus !== "ready"}
            >
              <h3>Receiver Console</h3>
              <p>
                Use a webcam-equipped device to capture the bursts with guided
                feedback and reconstruction.
              </p>
            </button>
          </div>
        )}
      </header>

      {role !== "none" && (
        <main className="layout">
          {role === "sender" ? (
            <SenderView
              callPythonJson={callPythonJson}
              onBack={() => setRole("none")}
            />
          ) : (
            <ReceiverView
              callPythonJson={callPythonJson}
              onBack={() => setRole("none")}
            />
          )}
        </main>
      )}
    </div>
  );
}
