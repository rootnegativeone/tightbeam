import { useCallback, useEffect, useRef, useState } from "react";

type Detector = {
  detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]>;
};
type DetectorCtor = new (options?: { formats?: string[] }) => Detector;

const MAX_CONSECUTIVE_FAILURES = 30;

export type CameraState = "idle" | "starting" | "running" | "error";
export type Facing = "environment" | "user";

export type ScannerInfo = {
  decoder: "native" | "wasm";
  resolution: string | null;
  facing: Facing;
  detections: number;
};

/**
 * The browser's own BarcodeDetector where it exists (Chrome on Android and
 * desktop); otherwise zxing-cpp compiled to WebAssembly (always the case on
 * iPhone). The WASM decoder replaced the ZXing JavaScript port, which failed
 * to find 3-31% of perfectly rendered dense codes in testing.
 */
const createDetector = async (): Promise<{
  detector: Detector;
  kind: ScannerInfo["decoder"];
}> => {
  const Native = (window as unknown as { BarcodeDetector?: DetectorCtor })
    .BarcodeDetector;
  if (Native) {
    return { detector: new Native({ formats: ["qr_code"] }), kind: "native" };
  }
  const [{ BarcodeDetector, prepareZXingModule }, { default: wasmUrl }] =
    await Promise.all([
      import("barcode-detector/ponyfill"),
      import("zxing-wasm/reader/zxing_reader.wasm?url"),
    ]);
  // Serve the WASM binary from this site rather than the package's CDN default.
  prepareZXingModule({
    overrides: {
      locateFile: (path: string, prefix: string) =>
        path.endsWith(".wasm") ? wasmUrl : prefix + path,
    },
    fireImmediately: true,
  });
  return {
    detector: new BarcodeDetector({ formats: ["qr_code"] }) as Detector,
    kind: "wasm",
  };
};

/** Camera + QR detection. Every decoded string is passed to ``onValue``. */
export const useScanner = (
  onValue: (value: string) => void | Promise<void>,
) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const detectorRef = useRef<Awaited<ReturnType<typeof createDetector>> | null>(
    null,
  );
  const onValueRef = useRef(onValue);
  onValueRef.current = onValue;
  const [state, setState] = useState<CameraState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<ScannerInfo>({
    decoder: "native",
    resolution: null,
    facing: "environment",
    detections: 0,
  });

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setState("idle");
  }, []);

  useEffect(() => stop, [stop]);

  const start = useCallback(
    async (facing: Facing = info.facing) => {
      setError(null);
      setState("starting");
      try {
        const detectorPromise = detectorRef.current
          ? Promise.resolve(detectorRef.current)
          : createDetector();
        const constraints = (mode: Facing) => ({
          video: {
            facingMode: { ideal: mode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        let stream: MediaStream;
        let used = facing;
        try {
          stream = await navigator.mediaDevices.getUserMedia(
            constraints(facing),
          );
        } catch (err) {
          if (facing !== "environment") throw err;
          stream = await navigator.mediaDevices.getUserMedia(
            constraints("user"),
          );
          used = "user";
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) throw new Error("Video element unavailable");
        video.srcObject = stream;
        await video.play();

        const { detector, kind } = (detectorRef.current =
          await detectorPromise);
        setInfo({
          decoder: kind,
          resolution: `${video.videoWidth}×${video.videoHeight}`,
          facing: used,
          detections: 0,
        });

        // Scan as fast as the decoder allows: each detect() is awaited, so a
        // slow decode simply means fewer attempts, never a backlog.
        let failures = 0;
        const loop = async () => {
          if (!videoRef.current?.srcObject) return;
          try {
            for (const { rawValue } of await detector.detect(
              videoRef.current,
            )) {
              if (rawValue) {
                setInfo((prev) => ({
                  ...prev,
                  detections: prev.detections + 1,
                }));
                await onValueRef.current(rawValue);
              }
            }
            failures = 0;
          } catch (err) {
            // A decoder that keeps throwing (e.g. its WASM failed to load)
            // would otherwise sit on "0 codes read" forever.
            if (++failures >= MAX_CONSECUTIVE_FAILURES) {
              console.error("QR decoder unavailable", err);
              stop();
              setState("error");
              setError(
                "The QR decoder couldn't load. Check the connection and try again.",
              );
              return;
            }
          }
          if (videoRef.current?.srcObject) {
            rafRef.current = requestAnimationFrame(loop);
          }
        };
        rafRef.current = requestAnimationFrame(loop);
        setState("running");
      } catch (err) {
        console.error(err);
        stop();
        setState("error");
        setError(
          err instanceof Error && err.name === "NotAllowedError"
            ? "Camera access was blocked. Allow it in your browser settings and try again."
            : "Couldn't start the camera.",
        );
      }
    },
    [info.facing, stop],
  );

  const flip = useCallback(() => {
    const next: Facing = info.facing === "environment" ? "user" : "environment";
    setInfo((prev) => ({ ...prev, facing: next }));
    if (streamRef.current) {
      stop();
      void start(next);
    }
  }, [info.facing, start, stop]);

  return { videoRef, state, error, info, start, stop, flip };
};
