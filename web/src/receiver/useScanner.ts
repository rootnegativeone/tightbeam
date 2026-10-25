import { useCallback, useEffect, useRef, useState } from "react";

type BarcodeDetectorLike = {
  detect: (source: CanvasImageSource) => Promise<{ rawValue: string }[]>;
};
type BarcodeDetectorCtor = new (options?: {
  formats?: string[];
}) => BarcodeDetectorLike;

export type CameraState = "idle" | "starting" | "running" | "error";
export type Facing = "environment" | "user";

export type ScannerInfo = {
  decoder: "native" | "zxing";
  resolution: string | null;
  facing: Facing;
  detections: number;
};

const nativeDetector = () => {
  const Detector = (
    window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }
  ).BarcodeDetector;
  return Detector ? new Detector({ formats: ["qr_code"] }) : null;
};

/**
 * Camera + QR detection. Uses the native BarcodeDetector where available and
 * falls back to ZXing (always the case on iPhone Safari). Every decoded string
 * is passed to ``onValue``.
 */
export const useScanner = (
  onValue: (value: string) => void | Promise<void>,
) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const stopZxingRef = useRef<(() => void) | null>(null);
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

  const emit = useCallback((value: string) => {
    setInfo((prev) => ({ ...prev, detections: prev.detections + 1 }));
    return onValueRef.current(value);
  }, []);

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    stopZxingRef.current?.();
    stopZxingRef.current = null;
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

        const detector = nativeDetector();
        setInfo({
          decoder: detector ? "native" : "zxing",
          resolution: `${video.videoWidth}×${video.videoHeight}`,
          facing: used,
          detections: 0,
        });

        if (detector) {
          const loop = async () => {
            if (!videoRef.current?.srcObject) return;
            try {
              for (const { rawValue } of await detector.detect(
                videoRef.current,
              )) {
                if (rawValue) await emit(rawValue);
              }
            } catch (err) {
              console.warn("Barcode detection failed; retrying", err);
            }
            rafRef.current = requestAnimationFrame(loop);
          };
          rafRef.current = requestAnimationFrame(loop);
        } else {
          const [browser, library] = await Promise.all([
            import("@zxing/browser"),
            import("@zxing/library"),
          ]);
          const reader = new browser.BrowserQRCodeReader();
          // Decode from the stream already attached to <video> (the selected
          // camera) and keep the controls so stop() actually halts scanning.
          const controls = await reader.decodeFromVideoElement(
            video,
            (result, err) => {
              if (result) {
                void emit(result.getText());
              } else if (err && !(err instanceof library.NotFoundException)) {
                console.warn("ZXing scanner error", err);
              }
            },
          );
          if (video.srcObject === null) {
            controls.stop(); // stopped while starting
          } else {
            stopZxingRef.current = () => controls.stop();
          }
        }
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
    [emit, info.facing, stop],
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
