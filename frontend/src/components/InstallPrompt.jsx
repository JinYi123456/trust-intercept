import { useEffect, useState } from "react";
import { cx } from "../lib/ui";

/**
 * InstallPrompt — one-click "Install App" for the universal PWA.
 *
 * - Chromium desktop (Windows/Mac) & Android: listens for `beforeinstallprompt`
 *   and triggers the native install dialog on click.
 * - iOS Safari: there is no programmatic install API, so we show a small hint
 *   (Share → Add to Home Screen) instead of a broken button.
 */
export default function InstallPrompt() {
  const [deferredEvent, setDeferredEvent] = useState(null);
  const [installed, setInstalled] = useState(false);
  const [showIosHint, setShowIosHint] = useState(false);

  const isIos =
    typeof navigator !== "undefined" &&
    /iphone|ipad|ipod/i.test(navigator.userAgent) &&
    !window.navigator.standalone;

  useEffect(() => {
    function onBeforeInstallPrompt(event) {
      event.preventDefault();
      setDeferredEvent(event);
    }
    function onInstalled() {
      setInstalled(true);
      setDeferredEvent(null);
    }
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    if (!deferredEvent) return;
    deferredEvent.prompt();
    try {
      const choice = await deferredEvent.userChoice;
      if (choice && choice.outcome === "accepted") setInstalled(true);
    } catch (promptError) {
      // User dismissed or the dialog failed — just hide our button.
    }
    setDeferredEvent(null);
  }

  if (installed) return null;

  if (deferredEvent) {
    return (
      <button
        type="button"
        onClick={install}
        className="rounded-full border border-neon-green/60 bg-neon-green/10 px-3 py-1.5 font-mono text-[11px] font-bold tracking-wider text-neon-green shadow-glow-green transition hover:bg-neon-green/20"
        title="Install TRUST//INTERCEPT as a standalone app (home screen / desktop)"
      >
        ⬇ INSTALL APP
      </button>
    );
  }

  if (isIos) {
    return (
      <span className="relative">
        <button
          type="button"
          onClick={() => setShowIosHint((current) => !current)}
          className="rounded-full border border-slate-700 bg-space-900 px-3 py-1.5 font-mono text-[11px] font-bold tracking-wider text-slate-300"
        >
          ⬇ INSTALL APP
        </button>
        {showIosHint && (
          <span className="glass-panel absolute right-0 top-9 z-50 w-56 p-3 text-xs text-slate-300">
            On iPhone/iPad: tap <strong className="text-neon-cyan">Share</strong> in Safari, then choose{" "}
            <strong className="text-neon-cyan">Add to Home Screen</strong> to install TRUST//INTERCEPT as an app.
          </span>
        )}
      </span>
    );
  }

  return null;
}
