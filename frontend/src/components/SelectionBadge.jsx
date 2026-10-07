import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";
import { cx } from "../lib/ui";

/**
 * SelectionBadge — the in-app face of the TRUST//INTERCEPT browser-extension overlay.
 *
 * A global text-selection listener: whenever the user selects/highlights
 * text anywhere in the hub, a subtle floating cyber badge ("🔍 Analyze with
 * TRUST//INTERCEPT") appears near the selection. Clicking it copies the text into the
 * intake, switches to the Message tab, and kicks off live analysis — the
 * exact flow the Manifest V3 extension mirrors on third-party pages
 * (public/extension/*) via the same sessionStorage hand-off key.
 */
export default function SelectionBadge() {
  const navigate = useNavigate();
  const [badge, setBadge] = useState(null); // { x, y, text }
  const [busy, setBusy] = useState(false);
  const badgeRef = useRef(null);

  useEffect(() => {
    function onSelect(event) {
      if (badgeRef.current && badgeRef.current.contains(event.target)) return;
      const selection = window.getSelection();
      const text = selection ? selection.toString().trim() : "";
      if (!selection || selection.isCollapsed || text.length < 3) {
        setBadge(null);
        return;
      }
      // Ignore selections inside form fields (users editing their own text).
      const anchor = selection.anchorNode;
      const insideField =
        anchor &&
        anchor.parentElement &&
        anchor.parentElement.closest("input, textarea, [contenteditable]");
      if (insideField) {
        setBadge(null);
        return;
      }
      const rect = selection.getRangeAt(0).getBoundingClientRect();
      setBadge({
        x: Math.max(8, Math.min(rect.left, window.innerWidth - 220)),
        y: Math.max(8, rect.top - 40),
        text: text.slice(0, 8000),
      });
    }

    function onClear() {
      setBadge(null);
    }

    document.addEventListener("mouseup", onSelect);
    // Clear on scroll/keypress — NOT on selectionchange (which fires right
    // after mouseup and would immediately dismiss the fresh badge).
    window.addEventListener("scroll", onClear, true);
    document.addEventListener("keydown", onClear);
    return () => {
      document.removeEventListener("mouseup", onSelect);
      window.removeEventListener("scroll", onClear, true);
      document.removeEventListener("keydown", onClear);
    };
  }, []);

  async function analyze() {
    if (!badge || busy) return;
    setBusy(true);
    try {
      const view = await api.submitCase({ input_type: "text", text: badge.text });
      sessionStorage.setItem("trust-intercept_selected_text", badge.text);
      setBadge(null);
      navigate(`/case/${view.case.id}/review`);
    } catch {
      setBusy(false);
    }
  }

  if (!badge) return null;

  return (
    <div
      ref={badgeRef}
      role="button"
      tabIndex={0}
      aria-label="Analyze the selected text with TRUST//INTERCEPT"
      onClick={analyze}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") analyze();
      }}
      className={cx(
        "animate-float-in fixed z-[90] cursor-pointer rounded-full border border-neon-cyan/60 bg-[#0B1120]/95 px-3.5 py-1.5",
        "font-mono text-xs font-bold tracking-wider text-neon-cyan shadow-glow-cyan backdrop-blur-xl transition hover:bg-neon-cyan/15"
      )}
      style={{ left: badge.x, top: badge.y }}
    >
      {busy ? "◌ INVESTIGATING…" : "🔍 ANALYZE WITH TRUST//INTERCEPT"}
    </div>
  );
}
