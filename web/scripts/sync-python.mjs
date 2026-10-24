// Copy the shared Python package from the repo root into public/ so Vite
// serves it to Pyodide. common/ is the source of truth; the copy is gitignored.
import { cpSync, existsSync, rmSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(webRoot, "..", "common");
const target = join(webRoot, "public", "python", "common");

if (!existsSync(source)) {
  console.error(`sync-python: source package not found at ${source}`);
  process.exit(1);
}

rmSync(target, { recursive: true, force: true });
cpSync(source, target, {
  recursive: true,
  filter: (path) =>
    !path.includes("__pycache__") &&
    (statSync(path).isDirectory() || path.endsWith(".py")),
});
console.log(`sync-python: copied ${source} -> ${target}`);
