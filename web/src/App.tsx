import { useEffect, useState } from "react";
import { usePython } from "./lib/python";
import { ReceiverView } from "./receiver/ReceiverView";
import { SenderView } from "./sender/SenderView";
import "./App.css";

declare global {
  interface Window {
    __TIGHTBEAM_BUILD?: string;
  }
}

type Route = "home" | "send" | "receive";

const routeFromHash = (): Route =>
  window.location.hash === "#send"
    ? "send"
    : window.location.hash === "#receive"
      ? "receive"
      : "home";

const useHashRoute = () => {
  const [route, setRoute] = useState<Route>(routeFromHash);
  useEffect(() => {
    const onChange = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const go = (next: Route) => {
    window.location.hash = next === "home" ? "" : next;
    setRoute(next);
  };
  return [route, go] as const;
};

const Wordmark = () => (
  <span className="wordmark">
    <svg className="wordmark-mark" viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="var(--beam)" />
      <rect x="4" y="6" width="7" height="12" rx="1.5" fill="#fff" />
      <path
        d="M13 9.5 20 7M13 14.5l7 2.5"
        stroke="#fff"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
    Tightbeam
  </span>
);

export default function App() {
  const python = usePython();
  const [route, go] = useHashRoute();
  const ready = python.status === "ready";
  const build = window.__TIGHTBEAM_BUILD ?? "dev";

  if (route !== "home") {
    return (
      <div className={`app is-${route}`}>
        <header className="topbar">
          <button className="topbar-home" onClick={() => go("home")}>
            <Wordmark />
          </button>
          <span className="topbar-title">
            {route === "send" ? "Send" : "Receive"}
          </span>
        </header>
        <main>
          {!ready ? (
            <div className="loading">
              {python.status === "error"
                ? `Couldn't load the decoder: ${python.error}`
                : "Getting ready…"}
            </div>
          ) : route === "send" ? (
            <SenderView call={python.call} />
          ) : (
            <ReceiverView call={python.call} />
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app is-home">
      <main className="home">
        <Wordmark />
        <h1>
          Get data off locked-down devices with just a screen and a camera.
        </h1>
        <p className="lede">
          No network, no cables, no pairing. The device shows a stream of codes;
          a phone scans them and rebuilds the data, verified end to end.
        </p>
        <div className="choices">
          <button className="choice" onClick={() => go("send")}>
            <span className="choice-title">Send</span>
            <span className="choice-body">Show codes on this screen.</span>
          </button>
          <button className="choice" onClick={() => go("receive")}>
            <span className="choice-title">Receive</span>
            <span className="choice-body">Scan with this device's camera.</span>
          </button>
        </div>
        <ol className="how">
          <li>
            <strong>Stream</strong> The sender loops through codes, several per
            second.
          </li>
          <li>
            <strong>Scan</strong> Missed frames don't matter: any big-enough
            subset rebuilds the data.
          </li>
          <li>
            <strong>Verify</strong> The result is checked against the sender's
            fingerprint.
          </li>
        </ol>
        <footer className="home-footer">
          {ready
            ? "Ready"
            : python.status === "error"
              ? `Decoder failed to load: ${python.error}`
              : "Loading decoder…"}{" "}
          · build {build}
        </footer>
      </main>
    </div>
  );
}
