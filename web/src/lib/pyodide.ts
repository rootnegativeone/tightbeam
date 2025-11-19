type PyodideInstance = {
  FS: {
    mkdirTree: (path: string) => void;
    writeFile: (path: string, data: string, opts: { encoding: string }) => void;
  };
  runPythonAsync: (code: string) => Promise<any>;
};

type LoadPyodideFn = (options: {
  indexURL: string;
}) => Promise<PyodideInstance>;

declare global {
  interface Window {
    loadPyodide?: LoadPyodideFn;
  }
}

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js";

const PYTHON_FILES = [
  "common/__init__.py",
  "common/fountain/__init__.py",
  "common/fountain/encoder.py",
  "common/fountain/decoder.py",
  "common/fountain/matrix.py",
  "common/fountain/sim.py",
  "common/shared/__init__.py",
  "common/shared/demo_payloads.py",
  "common/shared/metrics.py",
  "common/shared/utils.py",
  "sim_payload.py",
  "simulation.py",
] as const;

let pyodidePromise: Promise<PyodideInstance> | null = null;

async function loadPyodideScript(): Promise<void> {
  if (window.loadPyodide) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = PYODIDE_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () =>
      reject(new Error("Failed to load Pyodide runtime from CDN"));
    document.head.appendChild(script);
  });
}

async function primeFilesystem(pyodide: PyodideInstance) {
  const dirs = ["common", "common/fountain", "common/shared"];
  for (const dir of dirs) {
    try {
      pyodide.FS.mkdirTree(dir);
    } catch (_err) {
      /* directory already exists */
    }
  }

  for (const path of PYTHON_FILES) {
    const response = await fetch(`/python/${path}`);
    if (!response.ok) {
      throw new Error(`Unable to fetch ${path} (${response.status})`);
    }
    const source = await response.text();
    const absolutePath = path.startsWith("/") ? path : `/${path}`;
    const dirname = absolutePath.slice(0, absolutePath.lastIndexOf("/"));
    if (dirname) {
      try {
        pyodide.FS.mkdirTree(dirname);
      } catch (_err) {
        /* already exists */
      }
    }
    pyodide.FS.writeFile(absolutePath, source, { encoding: "utf8" });
  }

  await pyodide.runPythonAsync(
    `
import sys
if "." not in sys.path:
    sys.path.append("/")
from simulation import (
    simulate_transfer,
    prepare_broadcast,
    prepare_broadcast_from_base64,
    reset_receiver,
    receiver_add_symbol,
    receiver_status,
)
`.trim(),
  );
}

async function init(): Promise<PyodideInstance> {
  await loadPyodideScript();
  if (!window.loadPyodide) {
    throw new Error("Pyodide loader is unavailable");
  }
  const pyodide = await window.loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/",
  });
  await primeFilesystem(pyodide);
  return pyodide;
}

export async function ensurePyodide(): Promise<PyodideInstance> {
  if (!pyodidePromise) {
    pyodidePromise = init();
  }
  return pyodidePromise;
}
