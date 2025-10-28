import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { QRCodeSVG } from "qrcode.react";
import { ensurePyodide } from "./lib/pyodide";
import "./App.css";

type PyodideStatus = "idle" | "loading" | "ready" | "error";
type Role = "none" | "sender" | "receiver";
type DiagnosticMode = "standard" | "diagnostic";
type PlaybackState = "idle" | "playing" | "finished";

declare global {
  interface Window {
    __TIGHTBEAM_BUILD?: string;
  }
}

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

type SyncPayload = {
  sequence: number;
  ordinal: number;
  total: number;
  block_size: number;
  k: number;
  orig_len: number;
  integrity_check: boolean;
  confirmation_required: number;
};

type BroadcastFrameSync = {
  sequence: number;
  type: "sync";
  ordinal: number;
  total: number;
  content: SyncPayload;
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

type BroadcastFrame =
  | BroadcastFrameMeta
  | BroadcastFrameSymbol
  | BroadcastFrameSync;

type SyncConfig = {
  preamble_count: number;
  interval: number;
  confirmation_required: number;
};

type BroadcastPackage = {
  seed: number;
  payload_text: string;
  metadata: BroadcastMetadata;
  frames: BroadcastFrame[];
  total_frames: number;
  systematic_count: number;
  redundant_count: number;
  sync: SyncConfig;
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
  diagnosticMode: DiagnosticMode;
};

type ReceiverViewProps = {
  callPythonJson: CallPythonJson;
  onBack: () => void;
  diagnosticMode: DiagnosticMode;
  forceFallback: boolean;
  onToggleFallback: (next: boolean) => void;
};

type LockState = "idle" | "acquiring" | "locked";

type BarcodePoint = { x: number; y: number };

type BarcodeDetection = {
  rawValue: string;
  boundingBox?: DOMRectReadOnly;
  cornerPoints?: BarcodePoint[];
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
  lockState: LockState,
  lockProgress: number,
  lockTarget: number | null,
) => {
  if (lockState !== "locked") {
    if (lockProgress <= 0) {
      return "Hold steady on the sync frames until the lock engages.";
    }
    if (lockTarget) {
      return `Locking in… ${lockProgress}/${lockTarget} sync frames captured.`;
    }
    return "Sync burst detected — keep the QR centred to finish locking.";
  }
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

const SenderView = ({
  callPythonJson,
  onBack,
  diagnosticMode,
}: SenderViewProps) => {
  const [isPreparing, setIsPreparing] = useState(false);
  const [broadcast, setBroadcast] = useState<BroadcastPackage | null>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>("idle");
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const playbackTimer = useRef<number | null>(null);
  const [autoLoop, setAutoLoop] = useState(true);
  const [qrSize, setQrSize] = useState(() =>
    typeof window !== "undefined"
      ? Math.min(window.innerWidth * 0.45, 360)
      : 320,
  );
  const [sizeMultiplier, setSizeMultiplier] = useState(1);

  const frames = broadcast?.frames ?? [];
  const currentFrame = frames[currentFrameIndex];
  const totalFrames = broadcast?.total_frames ?? 0;
  const isDiagnostic = diagnosticMode === "diagnostic";
  const diagnosticFrame = useMemo(() => {
    if (!broadcast) {
      return null;
    }
    return broadcast.frames.find((frame) => frame.type === "sync") ?? null;
  }, [broadcast]);
  const displayFrame =
    isDiagnostic && diagnosticFrame ? diagnosticFrame : currentFrame;
  const displaySize = Math.round(qrSize * sizeMultiplier);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const updateSize = () => {
      setQrSize(Math.min(window.innerWidth * 0.45, 360));
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => {
      window.removeEventListener("resize", updateSize);
    };
  }, []);

  const handleToggleLoop = useCallback(() => {
    setAutoLoop((prev) => !prev);
  }, []);

  const handleSizeChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const next = Number.parseFloat(event.target.value);
      if (!Number.isNaN(next)) {
        setSizeMultiplier(next);
      }
    },
    [],
  );

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
        if (autoLoop) {
          idx = 0;
          setCurrentFrameIndex(0);
          return;
        }
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
  }, [broadcast, playbackState, stopPlaybackTimer, autoLoop]);

  useEffect(() => () => stopPlaybackTimer(), [stopPlaybackTimer]);

  const frameLabel = useMemo(() => {
    if (!displayFrame) {
      return "Ready";
    }
    if (isDiagnostic) {
      return "Diagnostic Sync Frame";
    }
    if (displayFrame.type === "sync") {
      return "Sync Frame";
    }
    if (displayFrame.type === "meta") {
      return "Metadata";
    }
    if (displayFrame.type === "symbol") {
      return displayFrame.systematic ? "Systematic Frame" : "Redundant Frame";
    }
    return "Frame";
  }, [displayFrame, isDiagnostic]);

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
            {displayFrame ? (
              <QRCodeSVG
                value={displayFrame.qr_value}
                size={displaySize}
                bgColor="#07130d"
                fgColor="#d5ffe7"
              />
            ) : (
              <div className="placeholder">
                {isDiagnostic
                  ? "Diagnostic mode — prepare broadcast to show sync frame"
                  : "Prepare broadcast"}
              </div>
            )}
            <div className="frame-meta">
              <div>
                {displayFrame
                  ? isDiagnostic
                    ? "Diagnostic sync frame"
                    : `Frame ${currentFrameIndex + 1} of ${totalFrames}`
                  : "Idle"}
              </div>
              <div>{frameLabel}</div>
              {displayFrame?.type === "sync" && (
                <div>
                  Sync {displayFrame.ordinal}/{displayFrame.total}
                </div>
              )}
              {displayFrame?.type === "symbol" && (
                <div>
                  d{displayFrame.degree} · {displayFrame.indices.join(", ")}
                </div>
              )}
              {displayFrame?.type === "meta" && broadcast && (
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
                disabled={!broadcast || isDiagnostic}
              >
                {isDiagnostic
                  ? "Start Burst"
                  : playbackState === "playing"
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
                  <li>
                    Sync preamble: {broadcast.sync.preamble_count} frames ·
                    reinserts every {broadcast.sync.interval} symbols
                  </li>
                </ul>
                <label className="loop-toggle">
                  <input
                    type="checkbox"
                    checked={autoLoop}
                    onChange={handleToggleLoop}
                  />
                  Auto loop bursts
                </label>
                <label className="size-control">
                  <span>QR size boost</span>
                  <input
                    type="range"
                    min="1"
                    max="1.4"
                    step="0.05"
                    value={sizeMultiplier}
                    onChange={handleSizeChange}
                  />
                  <span>{Math.round(sizeMultiplier * 100)}%</span>
                </label>
                {isDiagnostic && (
                  <p className="diagnostic-note">
                    Diagnostic mode pins the first sync frame for camera tests.
                    Click “Prepare broadcast” if you need a fresh sample.
                  </p>
                )}
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

const ReceiverView = ({
  callPythonJson,
  onBack,
  diagnosticMode,
  forceFallback,
  onToggleFallback,
}: ReceiverViewProps) => {
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
  const [lockState, setLockState] = useState<LockState>("idle");
  const [lockProgress, setLockProgress] = useState(0);
  const [lockTarget, setLockTarget] = useState<number | null>(null);
  const lastValueRef = useRef<string | null>(null);
  const animationRef = useRef<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<BarcodeDetectorLike | null>(null);
  const fallbackReaderRef = useRef<ZXingReader | null>(null);
  const fallbackNotFoundRef = useRef<ZXingNotFound | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const lockStateRef = useRef<LockState>("idle");
  const pendingMetadataRef = useRef<BroadcastMetadata | null>(null);
  const syncSequencesRef = useRef<Set<number>>(new Set());
  const lastSymbolTimestampRef = useRef<number | null>(null);
  const detectionStatsRef = useRef<{ lastTime: number; fps: number }>({
    lastTime: 0,
    fps: 0,
  });
  const isDiagnostic = diagnosticMode === "diagnostic";
  const [diagnosticEntries, setDiagnosticEntries] = useState<{
    timestamp: number;
    value: string;
    source: "native" | "fallback";
  }>([]);
  const [diagnosticStats, setDiagnosticStats] = useState<{
    fps: number;
    luminance: number;
  } | null>(null);
  const [diagnosticBoxes, setDiagnosticBoxes] = useState<
    { left: number; top: number; width: number; height: number }[]
  >([]);
  const ensureFallbackScanner = useCallback(async () => {
    if (fallbackReaderRef.current) {
      setUseFallbackScanner(true);
      setScannerSupported(true);
      return true;
    }
    try {
      const module = await import("@zxing/browser");
      fallbackReaderRef.current = new module.BrowserQRCodeReader();
      fallbackNotFoundRef.current = module.NotFoundException;
      setUseFallbackScanner(true);
      setScannerSupported(true);
      return true;
    } catch (err) {
      console.error("ZXing fallback unavailable", err);
      setScannerSupported(false);
      return false;
    }
  }, []);

  useEffect(() => {
    const Detector = (
      window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }
    ).BarcodeDetector;
    if (!forceFallback && Detector) {
      detectorRef.current = new Detector({ formats: ["qr_code"] });
      setScannerSupported(true);
    } else {
      detectorRef.current = null;
      void ensureFallbackScanner();
    }
  }, [forceFallback, ensureFallbackScanner]);

  useEffect(() => {
    lockStateRef.current = lockState;
  }, [lockState]);

  useEffect(() => {
    if (isDiagnostic) {
      setGuidance(
        "Diagnostic mode: point the camera at the sync frame and monitor detections below.",
      );
      return;
    }
    setGuidance(
      describeGuidance(status, metadata, lockState, lockProgress, lockTarget),
    );
  }, [isDiagnostic, status, metadata, lockState, lockProgress, lockTarget]);

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
    syncSequencesRef.current.clear();
    pendingMetadataRef.current = null;
    setLockState("idle");
    setLockProgress(0);
    setLockTarget(null);
    lastSymbolTimestampRef.current = null;
    setDiagnosticEntries([]);
    setDiagnosticStats(null);
    setDiagnosticBoxes([]);
    setCameraState("idle");
  }, [useFallbackScanner]);

  useEffect(() => () => stopCamera(), [stopCamera]);

  const requestResync = useCallback(() => {
    if (lockStateRef.current !== "locked") {
      return;
    }
    syncSequencesRef.current.clear();
    setLockState("acquiring");
    setLockProgress(0);
    setLockTarget(null);
    setStatus(null);
    setMetadata(null);
    lastSymbolTimestampRef.current = null;
  }, []);

  useEffect(() => {
    if (!isDiagnostic) {
      setDiagnosticEntries([]);
      setDiagnosticStats(null);
      setDiagnosticBoxes([]);
    }
  }, [isDiagnostic]);

  const computeLuminance = useCallback(() => {
    if (!isDiagnostic) {
      return 0;
    }
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      return 0;
    }
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) {
      return 0;
    }
    const sampleWidth = 160;
    const sampleHeight = Math.max(
      1,
      Math.round((height / width) * sampleWidth),
    );
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
      return 0;
    }
    canvas.width = sampleWidth;
    canvas.height = sampleHeight;
    context.drawImage(video, 0, 0, sampleWidth, sampleHeight);
    const { data } = context.getImageData(0, 0, sampleWidth, sampleHeight);
    let sum = 0;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      sum += 0.299 * r + 0.587 * g + 0.114 * b;
    }
    return sum / (data.length / 4);
  }, [isDiagnostic]);

  const logDetection = useCallback(
    (value: string, source: "native" | "fallback") => {
      if (!isDiagnostic) {
        return;
      }
      setDiagnosticEntries((prev) => {
        const next = [...prev, { timestamp: Date.now(), value, source }];
        return next.slice(-15);
      });
      const now = performance.now();
      const stats = detectionStatsRef.current;
      if (stats.lastTime) {
        const instantFps = 1000 / (now - stats.lastTime);
        stats.fps = stats.fps ? stats.fps * 0.5 + instantFps * 0.5 : instantFps;
      }
      stats.lastTime = now;
      const luminance = computeLuminance();
      setDiagnosticStats({
        fps: Number.isFinite(stats.fps) ? Number(stats.fps.toFixed(1)) : 0,
        luminance: Number.isFinite(luminance)
          ? Number(luminance.toFixed(1))
          : 0,
      });
    },
    [computeLuminance, isDiagnostic],
  );

  const clearDiagnosticLog = useCallback(() => setDiagnosticEntries([]), []);

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
      lastSymbolTimestampRef.current = Date.now();
    },
    [callPythonJson],
  );

  const handleSync = useCallback(
    async (payload: SyncPayload) => {
      const required = payload.confirmation_required;
      setLockTarget((current) => current ?? required);
      if (lockStateRef.current === "idle") {
        setLockState("acquiring");
      }
      if (!syncSequencesRef.current.has(payload.sequence)) {
        syncSequencesRef.current.add(payload.sequence);
        setLockProgress((prev) => {
          const next = Math.min(prev + 1, required);
          return next;
        });
      }
      pendingMetadataRef.current = {
        block_size: payload.block_size,
        k: payload.k,
        orig_len: payload.orig_len,
        integrity_check: payload.integrity_check,
      };
      if (
        syncSequencesRef.current.size >= required &&
        lockStateRef.current !== "locked"
      ) {
        setLockState("locked");
        setLockProgress(required);
        const pendingMeta = pendingMetadataRef.current;
        if (pendingMeta) {
          await handleMetadata(pendingMeta);
          pendingMetadataRef.current = null;
        }
      }
    },
    [handleMetadata],
  );

  useEffect(() => {
    if (cameraState !== "running") {
      return;
    }
    const timer = window.setInterval(() => {
      const lastSymbol = lastSymbolTimestampRef.current;
      if (lastSymbol === null) {
        return;
      }
      if (Date.now() - lastSymbol > 1500 && lockStateRef.current === "locked") {
        requestResync();
      }
    }, 400);
    return () => window.clearInterval(timer);
  }, [cameraState, requestResync]);

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
      lastSymbolTimestampRef.current = Date.now();
    },
    [callPythonJson],
  );

  const processValue = useCallback(
    async (value: string, source: "native" | "fallback") => {
      if (isDiagnostic) {
        setLastFrame(value);
        logDetection(value, source);
        return;
      }

      if (value === lastValueRef.current) {
        return;
      }
      lastValueRef.current = value;
      setLastFrame(value);
      logDetection(value, source);

      if (value.startsWith("Y:")) {
        try {
          const payload = JSON.parse(value.slice(2)) as SyncPayload;
          await handleSync(payload);
        } catch (err) {
          console.warn("Unable to parse sync payload", err);
        }
        return;
      }

      if (value.startsWith("M:")) {
        const payload = value.slice(2);
        const meta = JSON.parse(payload) as BroadcastMetadata;
        if (lockStateRef.current !== "locked") {
          pendingMetadataRef.current = meta;
          return;
        }
        await handleMetadata(meta);
        return;
      }

      if (!value.startsWith("S:") || lockStateRef.current !== "locked") {
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
    [handleMetadata, handleSymbol, handleSync, isDiagnostic, logDetection],
  );

  const scanLoop = useCallback(async () => {
    if (forceFallback || !detectorRef.current || !videoRef.current) {
      return;
    }
    try {
      const detections = await detectorRef.current.detect(videoRef.current);
      if (isDiagnostic) {
        if (detections.length > 0) {
          const video = videoRef.current;
          if (video) {
            const vw = video.videoWidth || 1;
            const vh = video.videoHeight || 1;
            const boxes = detections
              .map((det) => det.boundingBox)
              .filter((box): box is DOMRectReadOnly => Boolean(box))
              .map((box) => ({
                left: (box.x / vw) * 100,
                top: (box.y / vh) * 100,
                width: (box.width / vw) * 100,
                height: (box.height / vh) * 100,
              }));
            setDiagnosticBoxes(boxes);
          }
        } else {
          setDiagnosticBoxes([]);
        }
      }
      if (detections.length > 0) {
        const { rawValue } = detections[0];
        if (rawValue) {
          await processValue(rawValue, "native");
        }
      }
    } catch (err) {
      console.error(err);
      setCameraError("Scanner interrupted. Refresh to retry.");
      stopCamera();
      return;
    }
    animationRef.current = requestAnimationFrame(scanLoop);
  }, [forceFallback, isDiagnostic, processValue, stopCamera]);

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
      syncSequencesRef.current.clear();
      pendingMetadataRef.current = null;
      setLockState("idle");
      setLockProgress(0);
      setLockTarget(null);
      lastSymbolTimestampRef.current = null;
      if (forceFallback || !detectorRef.current) {
        const fallbackReady = await ensureFallbackScanner();
        if (!fallbackReady) {
          throw new Error("Fallback scanner unavailable");
        }
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
                if (isDiagnostic) {
                  setDiagnosticBoxes([]);
                }
                await processValue(text, "fallback");
              }
            } else if (
              err &&
              fallbackNotFoundRef.current &&
              err instanceof fallbackNotFoundRef.current
            ) {
              if (isDiagnostic) {
                setDiagnosticBoxes([]);
              }
            } else if (err) {
              console.warn("Fallback scanner error", err);
            }
          },
        );
        setCameraState("running");
      } else {
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
        if (!detectorRef.current) {
          setCameraError("QR detection unavailable in this browser.");
          setCameraState("error");
          return;
        }
        setCameraState("running");
        animationRef.current = requestAnimationFrame(scanLoop);
      }
    } catch (err) {
      console.error(err);
      setCameraState("error");
      setCameraError("Camera permission denied or unavailable.");
    }
  }, [
    ensureFallbackScanner,
    forceFallback,
    isDiagnostic,
    processValue,
    scanLoop,
    scannerSupported,
  ]);

  const coveragePercent = status ? formatPercent(status.coverage) : "0.0%";
  const overlayMessage =
    cameraState === "starting"
      ? "Starting camera…"
      : cameraState === "running"
        ? lockState === "locked"
          ? !metadata
            ? "Waiting for metadata frame to sync."
            : status?.decode_complete
              ? "Transfer complete — share the recovered payload."
              : "Keep the burst inside the guide."
          : lockState === "acquiring"
            ? lockTarget
              ? `Locking… ${lockProgress}/${lockTarget}`
              : "Locking onto sync burst…"
            : "Find the sync frames to begin locking."
        : "Tap Start Receiving to activate the camera.";
  const reticleClassName = [
    "capture-reticle",
    cameraState !== "running" ? "is-inactive" : "",
    lockState === "locked" ? "is-locked" : "",
    status?.decode_complete ? "is-complete" : "",
  ]
    .filter(Boolean)
    .join(" ");

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
            <div className="progress">
              <div className="progress-label">
                Sync lock &nbsp;
                {lockState === "locked"
                  ? "Locked"
                  : lockTarget
                    ? `${lockProgress}/${lockTarget}`
                    : "Idle"}
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill is-sync"
                  style={{
                    width:
                      lockState === "locked"
                        ? "100%"
                        : lockTarget
                          ? `${Math.min(lockProgress / lockTarget, 1) * 100}%`
                          : "0%",
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
            {isDiagnostic && (
              <div className="diagnostic-panel">
                <div className="diagnostic-stats">
                  <span>
                    FPS:&nbsp;
                    {diagnosticStats ? diagnosticStats.fps.toFixed(1) : "—"}
                  </span>
                  <span>
                    Luminance:&nbsp;
                    {diagnosticStats
                      ? Math.round(diagnosticStats.luminance)
                      : "—"}
                  </span>
                  <button className="link" onClick={clearDiagnosticLog}>
                    Clear log
                  </button>
                </div>
                <label className="diagnostic-toggle">
                  <input
                    type="checkbox"
                    checked={forceFallback}
                    onChange={() => onToggleFallback(!forceFallback)}
                  />
                  Force ZXing fallback
                </label>
                <div className="diagnostic-log">
                  {diagnosticEntries.length === 0 ? (
                    <p>No detections yet.</p>
                  ) : (
                    <ul>
                      {diagnosticEntries
                        .slice()
                        .reverse()
                        .map((entry) => (
                          <li key={entry.timestamp}>
                            <span className="diagnostic-timestamp">
                              {new Date(entry.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="diagnostic-source">
                              {entry.source}
                            </span>
                            <code>{entry.value}</code>
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="capture-stage">
            <div className="capture-outline">
              <video
                ref={videoRef}
                className="capture-video"
                playsInline
                autoPlay
                muted
              />
              <canvas ref={canvasRef} className="diagnostic-canvas" />
              <div className="capture-overlay">
                <div className={reticleClassName} />
                {isDiagnostic &&
                  diagnosticBoxes.map((box, index) => (
                    <span
                      key={index}
                      className="diagnostic-box"
                      style={{
                        left: `${box.left}%`,
                        top: `${box.top}%`,
                        width: `${box.width}%`,
                        height: `${box.height}%`,
                      }}
                    />
                  ))}
                <div className="capture-instruction">{overlayMessage}</div>
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
      </div>
    </section>
  );
};

export default function App() {
  const [pyodideStatus, setPyodideStatus] = useState<PyodideStatus>("idle");
  const [pyodideError, setPyodideError] = useState<string | null>(null);
  const [role, setRole] = useState<Role>("none");
  const [diagnosticMode, setDiagnosticMode] =
    useState<DiagnosticMode>("standard");
  const [forceFallback, setForceFallback] = useState(false);
  const buildInfo = window.__TIGHTBEAM_BUILD ?? "dev";

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
          <span className="build-tag">Build {buildInfo}</span>
        </div>
        <div className="diagnostic-controls">
          <label>
            <input
              type="checkbox"
              checked={diagnosticMode === "diagnostic"}
              onChange={(event) => {
                const next = event.target.checked ? "diagnostic" : "standard";
                setDiagnosticMode(next);
                if (!event.target.checked) {
                  setForceFallback(false);
                }
              }}
            />
            Diagnostic mode
          </label>
          {diagnosticMode === "diagnostic" && (
            <label>
              <input
                type="checkbox"
                checked={forceFallback}
                onChange={(event) => setForceFallback(event.target.checked)}
              />
              Force ZXing fallback
            </label>
          )}
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
              diagnosticMode={diagnosticMode}
            />
          ) : (
            <ReceiverView
              callPythonJson={callPythonJson}
              onBack={() => setRole("none")}
              diagnosticMode={diagnosticMode}
              forceFallback={forceFallback}
              onToggleFallback={setForceFallback}
            />
          )}
        </main>
      )}
    </div>
  );
}
