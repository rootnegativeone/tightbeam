import { useCallback, useEffect, useState } from "react";
import { ensurePyodide } from "./pyodide";
import type { CallPythonJson } from "../types";

export type PythonStatus = "loading" | "ready" | "error";

const isDestroyable = (value: unknown): value is { destroy: () => void } =>
  Boolean(
    value &&
    typeof value === "object" &&
    typeof (value as { destroy?: unknown }).destroy === "function",
  );

/** Load the in-browser Python runtime and expose a JSON-returning call helper. */
export const usePython = () => {
  const [status, setStatus] = useState<PythonStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    ensurePyodide()
      .then(() => !cancelled && setStatus("ready"))
      .catch((err: unknown) => {
        console.error(err);
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const call = useCallback<CallPythonJson>(async (fnName, ...args) => {
    const pyodide = await ensurePyodide();
    const fn = pyodide.globals.get(fnName);
    if (!fn) {
      throw new Error(`Python function "${fnName}" is unavailable`);
    }
    try {
      const result = fn(...args);
      const text = typeof result === "string" ? result : result.toString();
      if (isDestroyable(result)) {
        result.destroy();
      }
      return JSON.parse(text);
    } finally {
      if (isDestroyable(fn)) {
        fn.destroy();
      }
    }
  }, []);

  return { status, error, call };
};
