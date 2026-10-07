import { useEffect, useState } from "react";
import { cx } from "../lib/ui";

/**
 * VoiceExplanation — accessibility aid for elderly / low-vision users.
 *
 * Reads the verdict and plain-language warnings aloud using the native browser
 * Web Speech API (`window.speechSynthesis`) — no cloud service, no API key,
 * works offline, and requires only a click (a user gesture, which is exactly
 * what autoplay policies require anyway).
 */
export default function VoiceExplanation({ script, className }) {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    return () => {
      if (supported) window.speechSynthesis.cancel();
    };
  }, [supported]);

  // If the verdict changes mid-speech, stop rather than read stale text.
  useEffect(() => {
    if (supported && speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [script]);

  function toggle() {
    if (!supported || !script) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(script);
    utterance.lang = "en-US";
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={!supported || !script}
      title={
        supported
          ? "Read the verdict aloud (Web Speech API — on-device, no cloud service)"
          : "Your browser does not support speech synthesis"
      }
      className={cx(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[11px] font-bold tracking-wider transition",
        speaking
          ? "border-neon-red/60 bg-neon-red/10 text-neon-red shadow-glow-red-soft"
          : "border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/20 shadow-glow-cyan-soft",
        (!supported || !script) && "cursor-not-allowed border-slate-800 bg-space-950 text-slate-600 opacity-60 shadow-none"
      )}
    >
      <span aria-hidden="true">{speaking ? "⏹" : "🔊"}</span>
      {speaking ? "Stop reading" : "Voice explanation"}
    </button>
  );
}
