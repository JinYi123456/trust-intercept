import { useEffect, useRef, useState } from "react";
import { cx } from "../lib/ui";

/**
 * AudioWaveform — interactive spectrum/waveform preview card.
 *
 * Decodes the selected audio with the browser's WebAudio API (offline, no
 * uploads) and renders a neon waveform with a live File playback. During
 * analysis it switches to a scanning sweep that highlights the waveform as
 * TRUST//INTERCEPT "listens" — a visual echo of the backend's local spectral pass.
 */
export default function AudioWaveform({ file, scanning = false }) {
  const [peaks, setPeaks] = useState(null); // normalised amplitude bars
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);
  const rafRef = useRef(0);
  const urlRef = useRef(null);

  useEffect(() => {
    setPeaks(null);
    setDuration(0);
    setProgress(0);
    setPlaying(false);
    setError(null);

    if (!file) return undefined;

    // Revoke the previous object URL to avoid leaks.
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    const url = URL.createObjectURL(file);
    urlRef.current = url;

    let cancelled = false;

    async function decode() {
      try {
        const arrayBuffer = await file.arrayBuffer();
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) throw new Error("WebAudio unavailable in this browser.");
        const context = new AudioCtx();
        const decoded = await context.decodeAudioData(arrayBuffer.slice(0));
        if (cancelled) {
          context.close();
          return;
        }
        // Downsample the first channel into ~90 amplitude bars.
        const channel = decoded.getChannelData(0);
        const bars = 90;
        const block = Math.max(1, Math.floor(channel.length / bars));
        const values = [];
        for (let i = 0; i < bars; i += 1) {
          let sum = 0;
          const start = i * block;
          for (let j = 0; j < block; j += 1) {
            sum += Math.abs(channel[start + j] || 0);
          }
          values.push(sum / block);
        }
        const max = Math.max(0.02, ...values);
        setPeaks(values.map((v) => v / max));
        setDuration(decoded.duration);
        context.close();
      } catch (decodeError) {
        if (!cancelled) setError("Waveform preview unavailable for this format — analysis still works.");
      }
    }

    decode();
    return () => {
      cancelled = true;
      context_cleanup();
    };

    function context_cleanup() {
      /* placeholder — real cleanup happens in the shared effect below */
    }
  }, [file]);

  // Shared object-URL cleanup.
  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    []
  );

  // Playback progress ring for the play button.
  useEffect(() => {
    const tick = () => {
      const el = audioRef.current;
      if (el && el.duration) setProgress(el.currentTime / el.duration);
      rafRef.current = requestAnimationFrame(tick);
    };
    if (playing) rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing]);

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      el.play().catch(() => setError("Playback blocked by the browser."));
      setPlaying(true);
    }
  }

  const fmt = (seconds) => {
    if (!Number.isFinite(seconds) || seconds <= 0) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="glass-sub relative overflow-hidden p-4">
      {/* Waveform / scan visualization */}
      <div className="flex h-24 items-center gap-[2px]" aria-hidden="true">
        {peaks
          ? peaks.map((value, index) => {
              const passed = progress > 0 && index / peaks.length <= progress;
              const scanHit = scanning && Math.abs(index / peaks.length - ((Date.now() / 24 % 100) / 100)) < 0.05;
              return (
                <span
                  key={index}
                  className={cx(
                    "w-full min-w-[2px] rounded-full transition-all duration-150",
                    passed ? "bg-neon-green/80" : "bg-neon-cyan/70"
                  )}
                  style={{
                    height: `${Math.max(6, value * 96)}%`,
                    boxShadow: scanHit
                      ? "0 0 10px 2px rgba(255,0,85,.8)"
                      : passed
                      ? "0 0 6px rgba(0,230,118,.5)"
                      : "0 0 6px rgba(0,229,255,.35)",
                  }}
                />
              );
            })
          : [...Array(48)].map((_, index) => (
              <span
                key={index}
                className={cx(
                  "w-full min-w-[2px] rounded-full bg-slate-700/60",
                  scanning && "animate-pulse-glow"
                )}
                style={{ height: `${20 + ((index * 37) % 60)}%` }}
              />
            ))}
      </div>

      {/* Controls */}
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={togglePlay}
          disabled={!peaks}
          aria-label={playing ? "Pause audio preview" : "Play audio preview"}
          className={cx(
            "grid h-10 w-10 shrink-0 place-items-center rounded-full border text-sm transition",
            peaks
              ? "border-neon-cyan/60 bg-neon-cyan/15 text-neon-cyan hover:bg-neon-cyan/25"
              : "cursor-not-allowed border-slate-700 text-slate-600"
          )}
        >
          {playing ? "⏸" : "▶"}
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-[11px] font-bold tracking-wider text-slate-300">
            {file ? file.name : "No audio selected"}
          </p>
          <p className="font-mono text-[10px] text-slate-500">
            {duration ? fmt(duration) : "--:--"}
            {scanning && <span className="ml-2 animate-pulse-glow text-neon-red">◉ ANALYSING SPECTRUM…</span>}
          </p>
        </div>
      </div>

      <audio ref={audioRef} src={urlRef.current || undefined} onEnded={() => setPlaying(false)} className="hidden" />

      {error && <p className="mt-2 font-mono text-[10px] text-gold-neon">{error}</p>}
    </div>
  );
}
