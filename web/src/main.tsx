import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

declare global {
  interface Window {
    __TIGHTBEAM_BUILD?: string;
  }
}

declare const __BUILD_HASH__: string | undefined;

window.__TIGHTBEAM_BUILD =
  (__BUILD_HASH__ && __BUILD_HASH__.trim() !== ""
    ? __BUILD_HASH__
    : undefined) ??
  (import.meta.env.VITE_APP_BUILD as string | undefined) ??
  (import.meta.env.MODE as string | undefined) ??
  "dev";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
