import { useCallback, useEffect, useRef, useState } from "react";
import type {
  BroadcastMetadata,
  CallPythonJson,
  ReceiverStatus,
  SyncInfo,
} from "../types";

export type LockState = "idle" | "acquiring" | "locked";

export type RecoveredPayload = { text: string; isBase64: boolean };

const DUPLICATE_WINDOW_MS = 400;
const RESYNC_AFTER_MS = 4500;
const ETA_WINDOW_MS = 8000;
const MAX_EARLY_SYMBOLS = 600;

/**
 * Receiver session state: sync lock, session metadata, decoder status and the
 * recovered payload. Feed every scanned string to ``handleValue``.
 */
export const useTransfer = (call: CallPythonJson, onComplete: () => void) => {
  const [lock, setLock] = useState<{
    state: LockState;
    progress: number;
    target: number;
  }>({
    state: "idle",
    progress: 0,
    target: 4,
  });
  const [metadata, setMetadata] = useState<BroadcastMetadata | null>(null);
  const [status, setStatus] = useState<ReceiverStatus | null>(null);
  const [payload, setPayload] = useState<RecoveredPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null);
  const [lockedAt, setLockedAt] = useState<number | null>(null);

  const lockRef = useRef(lock);
  lockRef.current = lock;
  const metadataRef = useRef<BroadcastMetadata | null>(null);
  const ordinalsRef = useRef<{ session: string | null; seen: Set<number> }>({
    session: null,
    seen: new Set(),
  });
  const lastValueRef = useRef<{ value: string; at: number } | null>(null);
  const lastSymbolAtRef = useRef<number | null>(null);
  const historyRef = useRef<{ at: number; rank: number }[]>([]);
  // Data frames seen before the first sync frame; replayed once locked.
  const earlySymbolsRef = useRef<string[]>([]);
  const completeRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const reset = useCallback(() => {
    setLock({ state: "idle", progress: 0, target: 4 });
    setMetadata(null);
    metadataRef.current = null;
    setStatus(null);
    setPayload(null);
    setError(null);
    setEtaSeconds(null);
    setLockedAt(null);
    ordinalsRef.current = { session: null, seen: new Set() };
    lastValueRef.current = null;
    lastSymbolAtRef.current = null;
    historyRef.current = [];
    earlySymbolsRef.current = [];
    completeRef.current = false;
  }, []);

  const applyMetadata = useCallback(
    async (meta: BroadcastMetadata) => {
      if (metadataRef.current?.session_id === meta.session_id) {
        return;
      }
      const result = await call("reset_receiver", JSON.stringify(meta));
      if (result.error) {
        setError(result.error);
        return;
      }
      metadataRef.current = meta;
      setMetadata(meta);
      setStatus(null);
      setPayload(null);
      setLockedAt(Date.now());
      historyRef.current = [];
      completeRef.current = false;
    },
    [call],
  );

  const handleSync = useCallback(
    async (info: SyncInfo) => {
      const {
        ordinal,
        total: _total,
        confirmation_required: target,
        ...meta
      } = info;
      const ordinals = ordinalsRef.current;
      if (ordinals.session !== meta.session_id) {
        ordinalsRef.current = { session: meta.session_id, seen: new Set() };
      }
      ordinalsRef.current.seen.add(ordinal);
      const progress = Math.min(ordinalsRef.current.seen.size, target);
      const current = lockRef.current;

      if (current.state === "locked") {
        // A new session from the sender (it was restarted): adopt it.
        if (
          metadataRef.current?.session_id !== meta.session_id &&
          progress >= target
        ) {
          await applyMetadata(meta);
        }
        return;
      }
      const next = {
        state: progress >= target ? "locked" : "acquiring",
        progress,
        target,
      } as const;
      setLock(next);
      lockRef.current = next;
      if (next.state === "locked") {
        await applyMetadata(meta);
      }
    },
    [applyMetadata],
  );

  const handleSymbol = useCallback(
    async (value: string) => {
      const result = (await call(
        "receiver_add_frame",
        value,
      )) as ReceiverStatus & {
        error?: string;
      };
      if (result.error) {
        return;
      }
      const now = Date.now();
      lastSymbolAtRef.current = now;
      setStatus(result);

      const history = historyRef.current;
      history.push({ at: now, rank: result.rank });
      while (history.length > 2 && now - history[0].at > ETA_WINDOW_MS) {
        history.shift();
      }
      const first = history[0];
      const gained = result.rank - first.rank;
      const span = (now - first.at) / 1000;
      setEtaSeconds(
        gained > 0 && span > 1 && !result.decode_complete
          ? ((result.k - result.rank) * span) / gained
          : null,
      );

      if (result.decode_complete && !completeRef.current) {
        completeRef.current = true;
        const recovered = await call("receiver_payload");
        if (!recovered.error) {
          setPayload({ text: recovered.text, isBase64: recovered.is_base64 });
        }
        onCompleteRef.current();
      } else if (result.phase === "error" && !completeRef.current) {
        completeRef.current = true;
        onCompleteRef.current();
      }
    },
    [call],
  );

  const handleValue = useCallback(
    async (value: string) => {
      const now = Date.now();
      const last = lastValueRef.current;
      if (last && last.value === value && now - last.at < DUPLICATE_WINDOW_MS) {
        return;
      }
      lastValueRef.current = { value, at: now };

      if (value.startsWith("Y:")) {
        const info = await call("receiver_parse_sync", value);
        if (info.error) {
          return;
        }
        await handleSync(info as SyncInfo);
        const session = metadataRef.current?.session_id.replace(/^TB-/, "");
        const early = earlySymbolsRef.current;
        earlySymbolsRef.current = [];
        for (const frame of early) {
          if (session && frame.split(":", 2)[1] === session) {
            await handleSymbol(frame);
          }
        }
        return;
      }
      if (!value.startsWith("S:") || completeRef.current) {
        return;
      }
      if (!metadataRef.current) {
        const early = earlySymbolsRef.current;
        if (early.length < MAX_EARLY_SYMBOLS && !early.includes(value)) {
          early.push(value);
        }
        return;
      }
      // Frames from another session are rejected by the Python side.
      await handleSymbol(value);
    },
    [call, handleSync, handleSymbol],
  );

  // Drop back to "acquiring" if symbols stop arriving (camera moved away);
  // the session and everything received so far are kept.
  useEffect(() => {
    if (lock.state !== "locked") {
      return;
    }
    const timer = window.setInterval(() => {
      const last = lastSymbolAtRef.current;
      if (
        !completeRef.current &&
        last !== null &&
        Date.now() - last > RESYNC_AFTER_MS
      ) {
        ordinalsRef.current.seen.clear();
        const next = {
          state: "acquiring",
          progress: 0,
          target: lockRef.current.target,
        } as const;
        setLock(next);
        lockRef.current = next;
        lastSymbolAtRef.current = null;
        setEtaSeconds(null);
      }
    }, 500);
    return () => window.clearInterval(timer);
  }, [lock.state]);

  return {
    lock,
    metadata,
    status,
    payload,
    error,
    etaSeconds,
    lockedAt,
    handleValue,
    reset,
  };
};
