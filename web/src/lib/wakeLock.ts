import { useEffect } from "react";

type WakeLockSentinelLike = { release: () => Promise<void> };
type WakeLockLike = {
  request: (type: "screen") => Promise<WakeLockSentinelLike>;
};

/** Keep the screen awake while ``active`` (sending or scanning). Best effort. */
export const useWakeLock = (active: boolean) => {
  useEffect(() => {
    const wakeLock = (navigator as unknown as { wakeLock?: WakeLockLike })
      .wakeLock;
    if (!active || !wakeLock) {
      return;
    }
    let sentinel: WakeLockSentinelLike | null = null;
    let cancelled = false;
    const acquire = () => {
      wakeLock
        .request("screen")
        .then((lock) => {
          if (cancelled) {
            void lock.release();
          } else {
            sentinel = lock;
          }
        })
        .catch(() => undefined);
    };
    // The lock is dropped whenever the tab is hidden; take it again on return.
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        acquire();
      }
    };
    acquire();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisible);
      void sentinel?.release();
    };
  }, [active]);
};
