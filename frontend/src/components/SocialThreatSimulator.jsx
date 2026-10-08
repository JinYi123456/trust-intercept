import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";
import { cx } from "../lib/ui";

/**
 * SocialThreatSimulator — "background listener service" demo.
 *
 * Simulates an incoming Telegram/WhatsApp notification containing a suspected
 * scam. When the user has granted OS notification permission, the simulated
 * message pops as a REAL system-level notification banner (Windows / macOS /
 * Android — visible even when the browser is minimized); clicking the OS
 * banner focuses TRUST//INTERCEPT and pipes the message straight into the live pipeline
 * via POST /case. In-page floating toasts remain as the visual fallback (and
 * for the period before permission is granted / when the API is unavailable).
 */

const THREATS = [
  {
    id: "telegram_parcel",
    app: "Telegram",
    accent: "#229ED9",
    icon: "✈️",
    sender: "+65 8xxx · joins channel",
    preview: "SINGPOST: Your parcel is HELD… unpaid delivery fee of $1.99…",
    text:
      "SINGPOST: Your parcel is HELD at our depot due to an unpaid delivery fee of $1.99. " +
      "Settle within 24 hours or it will be returned: https://bit.ly/parcel-hold-9x2 — " +
      "enter your IC number S1234567D, card details 4111 1111 1111 1111 and the OTP we sent. Urgent!",
  },
  {
    id: "whatsapp_bank",
    app: "WhatsApp",
    accent: "#25D366",
    icon: "💬",
    sender: "+44 7xxx · unknown number",
    preview: "DHL Express: customs charge of $2.99… verify your card…",
    text:
      "DHL Express: We could not deliver your shipment D-9823. Pay the customs charge of $2.99 " +
      "to reschedule today: https://dhl-parapl.red/track — verify your identity with your card " +
      "number and the OTP. Final notice!",
  },
  {
    id: "telegram_prize",
    app: "Telegram",
    accent: "#229ED9",
    icon: "✈️",
    sender: "broadcast channel",
    preview: "Congratulations! You won a $500 voucher… claim within 12 hours…",
    text:
      "Congratulations! You have won the Singtel lucky draw. Claim your $500 shopping voucher " +
      "within 12 hours: https://bit.ly/claim-prize-now — enter your mobile number and the OTP " +
      "code to receive your prize.",
  },
];

const AUTO_DISMISS_MS = 9000;

/** Cached Notification API availability + permission state. */
export function useNativeNotifications() {
  const supported =
    typeof window !== "undefined" &&
    "Notification" in window &&
    typeof window.Notification?.requestPermission === "function";
  const [permission, setPermission] = useState(
    supported ? Notification.permission : "unsupported"
  );

  /** Must be called from a user gesture (the header button click). */
  const requestPermission = useCallback(async () => {
    if (!supported) return "unsupported";
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result;
    } catch {
      return "denied";
    }
  }, [supported]);

  return { supported, permission, requestPermission };
}

/** Fire a native OS banner; returns true if the OS accepted it. */
function showNativeNotification(registration, threat) {
  if (!registration) return false;
  const title = `${threat.app} · New message`;
  const options = {
    body: threat.preview,
    icon: "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    tag: `trust-intercept-sim-${threat.id}`,
    requireInteraction: false,
    silent: false,
    data: { threatId: threat.id, url: "/" },
  };
  try {
    const show = registration.showNotification
      ? registration.showNotification.bind(registration)
      : null;
    if (!show) return false;
    show(title, options);
    return true;
  } catch {
    return false;
  }
}

function ThreatToast({ threat, onDismiss, onInvestigate }) {
  const [progress, setProgress] = useState(100);
  const startRef = useRef(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = Math.max(0, 100 - ((Date.now() - startRef.current) / AUTO_DISMISS_MS) * 100);
      setProgress(remaining);
      if (remaining <= 0) onDismiss();
    }, 100);
    return () => clearInterval(timer);
  }, [onDismiss]);

  return (
    <div
      role="alertdialog"
      aria-label={`Simulated ${threat.app} notification`}
      className="glass-panel animate-float-in fixed right-4 top-4 z-[100] w-[min(92vw,22rem)] cursor-pointer overflow-hidden p-0 shadow-glow-red"
      onClick={onInvestigate}
    >
      <div className="flex items-center gap-3 border-b border-slate-800/80 bg-slate-900/80 px-4 py-2.5">
        <span className="text-lg" aria-hidden="true">{threat.icon}</span>
        <div className="min-w-0">
          <p className="truncate text-xs font-bold text-slate-200">
            {threat.app} · <span className="text-slate-400">{threat.sender}</span>
          </p>
        </div>
        <span className="ml-auto font-mono text-[10px] tracking-widest text-neon-red animate-pulse-glow">
          ● LIVE
        </span>
      </div>

      <div className="px-4 py-3">
        <p className="text-sm font-semibold text-slate-100">New message</p>
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{threat.preview}</p>
        <p className="mt-2.5 flex items-center gap-2 text-xs font-bold text-neon-cyan">
          <span className="rounded border border-neon-cyan/40 bg-neon-cyan/10 px-1.5 py-0.5 font-mono text-[10px] tracking-widest">
            TAP TO INVESTIGATE WITH TRUST//INTERCEPT
          </span>
        </p>
      </div>

      <div className="h-1 w-full bg-slate-800">
        <div className="h-full bg-gradient-to-r from-neon-red to-neon-gold transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}

export default function SocialThreatSimulator() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState(null); // threat currently shown as in-page toast
  const [busy, setBusy] = useState(false);
  const [nativeStatus, setNativeStatus] = useState("");
  const { supported, permission, requestPermission } = useNativeNotifications();
  const registrationRef = useRef(null);

  // Remember the PWA service-worker registration (needed for OS banners that
  // still work when the tab is minimized / in the background on Android).
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return undefined;
    let cancelled = false;
    navigator.serviceWorker.ready
      .then((registration) => {
        if (!cancelled) registrationRef.current = registration;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // A click on the NATIVE OS banner focuses TRUST//INTERCEPT and forwards the threat id
  // (see public/notification-handlers.js in the service worker). Replay it.
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return undefined;
    function onMessage(event) {
      const data = event.data || {};
      if (data.type !== "trust-intercept-simulated-threat") return;
      const threat = THREATS.find((item) => item.id === data.threatId);
      if (threat) investigate(threat);
    }
    navigator.serviceWorker.addEventListener("message", onMessage);
    return () => navigator.serviceWorker.removeEventListener("message", onMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const investigate = useCallback(async (threat) => {
    setMenuOpen(false);
    setActive(null);
    setBusy(true);
    try {
      const view = await api.submitCase({ input_type: "text", text: threat.text });
      navigate(`/case/${view.case.id}/review`);
    } catch (submitError) {
      setBusy(false);
    }
  }, [navigate]);

  /** Header button: enable native banners (user gesture), then open the menu. */
  async function onToggleMenu() {
    setMenuOpen((current) => !current);
    if (supported && permission === "default") {
      const result = await requestPermission();
      if (result === "granted") {
        setNativeStatus("OS notifications enabled — threats pop as real system banners");
        setTimeout(() => setNativeStatus(""), 5000);
      } else if (result === "denied") {
        setNativeStatus("OS banners blocked by the browser — using in-app toasts instead");
        setTimeout(() => setNativeStatus(""), 5000);
      }
    }
  }

  /** Menu item selected: pop the native OS banner (if allowed) + in-page toast. */
  function simulate(threat) {
    setMenuOpen(false);

    if (supported && permission === "granted") {
      let shown = false;
      const registration = registrationRef.current;
      shown = showNativeNotification(registration, threat);
      // Fallback: page-level Notification constructor (works while the tab is
      // focused on desktop even without an active service worker).
      if (!shown && typeof Notification === "function") {
        try {
          const n = new Notification(`${threat.app} · New message`, {
            body: threat.preview,
            icon: "/icons/icon-192.png",
            tag: `trust-intercept-sim-${threat.id}`,
            data: { threatId: threat.id, url: "/" },
          });
          n.onclick = (event) => {
            event.preventDefault();
            try {
              window.focus();
            } catch {
              /* best effort */
            }
            n.close();
            investigate(threat);
          };
          shown = true;
        } catch {
          shown = false;
        }
      }
    }

    // The in-page toast stays as the visible demo cue (it is what judges see
    // on screen) — the OS banner appears alongside it on desktop/Android.
    setActive(threat);
  }

  const badge =
    supported && permission === "granted"
      ? { text: "OS", title: "Native OS notifications enabled", cls: "border-neon-green/50 bg-neon-green/10 text-neon-green" }
      : supported && permission === "default"
        ? { text: "SETUP", title: "Click to enable native OS notifications", cls: "border-neon-gold/50 bg-neon-gold/10 text-neon-gold" }
        : { text: "APP", title: "In-app toast mode (Notification API unavailable)", cls: "border-slate-600 bg-slate-800 text-slate-300" };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={onToggleMenu}
        aria-expanded={menuOpen}
        title="Simulate an incoming Telegram/WhatsApp threat (background listener demo)"
        className={cx(
          "rounded-full border px-3 py-1.5 text-xs font-semibold transition",
          busy
            ? "border-neon-red/60 bg-neon-red/20 text-neon-red"
            : "border-neon-gold/50 bg-neon-gold/10 text-neon-gold hover:bg-neon-gold/20"
        )}
      >
        {busy ? "◉ PIPELINE LIVE…" : "◉ Simulate incoming threat"}
      </button>

      {menuOpen && (
        <div
          className="animate-float-in absolute right-0 top-10 z-50 w-72 rounded-xl border border-cyan-500/30 bg-[#0B1120]/95 shadow-2xl shadow-cyan-950/80 backdrop-blur-xl"
          role="menu"
          aria-label="Simulated threat picker"
        >
          <p className="label-cyber px-3 pb-1 pt-3">Inject a simulated social-app message</p>
          {THREATS.map((threat) => (
            <button
              key={threat.id}
              type="button"
              onClick={() => simulate(threat)}
              className="mx-1 flex w-[calc(100%-0.5rem)] items-center gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-slate-800/70"
            >
              <span
                className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-sm"
                style={{ backgroundColor: `${threat.accent}22`, border: `1px solid ${threat.accent}55` }}
                aria-hidden="true"
              >
                {threat.icon}
              </span>
              <span className="min-w-0">
                <span className="block text-xs font-bold text-slate-200">
                  {threat.app} — {threat.id.split("_")[1]}
                </span>
                <span className="block truncate text-[11px] text-muted">{threat.preview}</span>
              </span>
            </button>
          ))}
          {supported && permission === "denied" && (
            <div className="mx-2 mt-2 rounded-lg border border-gold-neon/50 bg-gold-neon/10 p-2.5">
              <p className="font-mono text-[10px] font-bold tracking-wider text-gold-neon">
                ⚠ OS NOTIFICATIONS BLOCKED
              </p>
              <p className="mt-1 text-[10px] leading-relaxed text-amber-100/80">
                Your browser is blocking system banners. To enable them: click the lock/gear icon
                in the address bar → Site settings → Notifications → Allow. TRUST//INTERCEPT falls back to
                in-app toasts meanwhile — every feature still works.
              </p>
            </div>
          )}
          <div className="mx-2 mb-2 mt-2 rounded-lg border border-slate-800 bg-slate-900/80 p-2.5">
            <p className="text-[10px] leading-relaxed text-muted">
              {nativeStatus ||
                (supported && permission === "granted"
                  ? "Native OS banners active — the system notification loads the threat on click, even when the window is minimized."
                  : supported && permission === "denied"
                    ? "In-app toast fallback active — enable notifications in browser settings for system banners."
                    : "Demo only — an in-app toast pops like an OS notification; the first click also requests OS notification permission. No real messaging app is read.")}
            </p>
          </div>
        </div>
      )}

      {active && (
        <ThreatToast
          threat={active}
          onDismiss={() => setActive(null)}
          onInvestigate={() => investigate(active)}
        />
      )}
    </div>
  );
}
