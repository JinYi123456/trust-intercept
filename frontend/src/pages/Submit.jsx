import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";
import AudioWaveform from "../components/AudioWaveform.jsx";
import CameraScanner from "../components/CameraScanner.jsx";
import LiveMetricsDashboard from "../components/LiveMetricsDashboard.jsx";
import RadarScan from "../components/RadarScan.jsx";
import { cx } from "../lib/ui";

const SAMPLE_SCAM =
  "SINGPOST: Your parcel is HELD at our depot due to an unpaid delivery fee of $1.99. " +
  "Settle within 24 hours or it will be returned: https://bit.ly/parcel-hold-9x2 — " +
  "enter your IC number S1234567D, card details 4111 1111 1111 1111 and the OTP we sent " +
  "to confirm delivery. Urgent! Call +65 9123 4567 immediately.";

const SAMPLE_LEGIT =
  "Hi Anna, your DHL delivery D-9823 is arriving today between 2-4 PM. " +
  "Track it here: https://www.dhl.com/track/D-9823. No action needed.";

const PIPELINE_STAGES = [
  "NORMALISING EVIDENCE — OCR / QR / PII REDACTION",
  "ROUTING CASE TO INVESTIGATION MODULES",
  "RUNNING TOOLS — REDIRECTS · WHOIS · REPUTATION",
  "SYNTHESISING EXPLAINABLE VERDICT",
];

const TABS = [
  { id: "text", label: "Message text", hint: "Paste a suspicious SMS or email body." },
  { id: "url", label: "URL", hint: "Paste a link you were asked to open." },
  { id: "image", label: "Screenshot / QR", hint: "Upload a screenshot or a QR-code image." },
  { id: "camera", label: "Live camera scan", hint: "Point your camera at a physical QR code — decoded on-device." },
  { id: "audio", label: "Audio / Voice call", hint: "Upload or record a suspicious voicemail or voice call for deepfake and coercion analysis." },
];

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result || "");
      const commaIndex = dataUrl.indexOf(",");
      resolve(commaIndex === -1 ? dataUrl : dataUrl.slice(commaIndex + 1));
    };
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsDataURL(file);
  });
}

export default function Submit() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [recorder, setRecorder] = useState(null);
  const [recording, setRecording] = useState(false);
  const [imageKind, setImageKind] = useState("screenshot"); // screenshot | qr
  const [submitting, setSubmitting] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState(null);
  const stageTimer = useRef(null);

  useEffect(() => () => stageTimer.current && clearInterval(stageTimer.current), []);

  const startStageAnimation = () => {
    setStage(0);
    stageTimer.current = setInterval(() => {
      setStage((current) => Math.min(current + 1, PIPELINE_STAGES.length - 1));
    }, 900);
  };

  const stopStageAnimation = () => {
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = null;
  };

  const canSubmit = (() => {
    if (submitting || tab === "camera") return false;
    if (tab === "text") return text.trim().length > 0;
    if (tab === "url") return url.trim().length > 0;
    if (tab === "audio") return Boolean(audioFile);
    return Boolean(file);
  })();

  async function runPipeline(payload) {
    setError(null);
    setSubmitting(true);
    startStageAnimation();
    try {
      const view = await api.submitCase(payload);
      navigate(`/case/${view.case.id}/review`);
    } catch (submitError) {
      setError(submitError.message);
      setSubmitting(false);
      stopStageAnimation();
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    const payload = {
      input_type:
        tab === "url" ? "url" : tab === "image" ? (imageKind === "qr" ? "qr_image" : "image") : "text",
      text: tab === "text" ? text : "",
      url: tab === "url" ? url.trim() : "",
      image_b64: "",
      image_filename: "",
      audio_b64: "",
      audio_filename: "",
    };

    if (tab === "image" && file) {
      payload.image_b64 = await fileToBase64(file);
      payload.image_filename = file.name;
    }
    if (tab === "audio" && audioFile) {
      payload.input_type = "audio";
      payload.audio_b64 = await fileToBase64(audioFile);
      payload.audio_filename = audioFile.name;
      payload.text = text;
    }
    await runPipeline(payload);
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Cyber hero */}
      <div className="mb-6 text-center sm:mb-8">
        <h1 className="text-2xl font-black tracking-tight text-slate-100 sm:text-3xl">
          Check a suspicious message
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-300 sm:text-base">
          Paste a message, drop a link, scan a QR code, upload a screenshot, or upload a suspicious
          voice call. TRUST//INTERCEPT checks the evidence and explains what it found in plain
          language — <strong className="text-slate-100">you decide</strong> what to do next.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel p-4 sm:p-6">
        {/* Input type tabs */}
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-slate-800/80 bg-space-950/70 p-1 sm:grid-cols-5" role="tablist">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              onClick={() => setTab(item.id)}
              className={cx(
                "rounded-lg px-2 py-2 font-mono text-[11px] font-bold tracking-wider transition sm:text-xs",
                tab === item.id
                  ? "bg-neon-cyan/15 text-neon-cyan ring-1 ring-neon-cyan/50 shadow-glow-cyan-soft"
                  : "text-muted hover:text-slate-300"
              )}
            >
              {item.label.toUpperCase()}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">{TABS.find((t) => t.id === tab)?.hint}</p>

        <div className="mt-4">
          {tab === "text" && (
            <div>
              <label htmlFor="message-text" className="sr-only">Message text</label>
              <textarea
                id="message-text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={7}
                placeholder="Paste the full SMS or email text here…"
                className="w-full resize-y rounded-lg border border-slate-700/80 bg-space-950/70 p-3 font-mono text-sm text-slate-200 placeholder:text-faint focus:border-neon-cyan/60 focus:outline-none focus:ring-2 focus:ring-neon-cyan/25"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setText(SAMPLE_SCAM)}
                  className="rounded-full border border-neon-red/40 bg-neon-red/10 px-3 py-1 font-mono text-[11px] font-bold tracking-wider text-neon-red hover:bg-neon-red/20"
                >
                  ⚠ LOAD SAMPLE: PARCEL-FEE SCAM SMS
                </button>
                <button
                  type="button"
                  onClick={() => setText(SAMPLE_LEGIT)}
                  className="rounded-full border border-neon-green/40 bg-neon-green/10 px-3 py-1 font-mono text-[11px] font-bold tracking-wider text-neon-green hover:bg-neon-green/20"
                >
                  ✓ LOAD SAMPLE: LEGITIMATE COURIER SMS
                </button>
              </div>
            </div>
          )}

          {tab === "url" && (
            <div>
              <label htmlFor="url-input" className="sr-only">URL</label>
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/track?parcel=…"
                className="w-full rounded-lg border border-slate-700/80 bg-space-950/70 p-3 font-mono text-sm text-slate-200 placeholder:text-faint focus:border-neon-cyan/60 focus:outline-none focus:ring-2 focus:ring-neon-cyan/25"
              />
              <p className="mt-2 text-xs text-muted">
                TRUST//INTERCEPT traces the redirect chain (≤5 hops), checks domain age and reputation —
                before you ever open it.
              </p>
            </div>
          )}

          {tab === "image" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Image type">
                {[
                  { id: "screenshot", label: "MESSAGE SCREENSHOT" },
                  { id: "qr", label: "QR CODE IMAGE" },
                ].map((option) => (
                  <label
                    key={option.id}
                    className={cx(
                      "flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 font-mono text-[11px] font-bold tracking-wider transition",
                      imageKind === option.id
                        ? "border-neon-cyan/60 bg-neon-cyan/10 text-neon-cyan shadow-glow-cyan-soft"
                        : "border-slate-700/80 text-muted hover:bg-slate-800/50"
                    )}
                  >
                    <input
                      type="radio"
                      name="image-kind"
                      value={option.id}
                      checked={imageKind === option.id}
                      onChange={() => setImageKind(option.id)}
                      className="sr-only"
                    />
                    {option.label}
                  </label>
                ))}
              </div>

              <label
                htmlFor="image-input"
                className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-space-950/60 p-6 text-center transition hover:border-neon-cyan/50 hover:bg-neon-cyan/5"
              >
                {file ? (
                  <img
                    src={URL.createObjectURL(file)}
                    alt="Selected upload preview"
                    className="max-h-48 rounded-lg border border-slate-700 object-contain"
                  />
                ) : (
                  <>
                    <span className="text-3xl" aria-hidden="true">🖼️</span>
                    <span className="mt-2 text-sm font-medium text-slate-300">Click to choose an image</span>
                    <span className="mt-1 text-xs text-muted">
                      Screenshots are OCR&apos;d locally; QR codes are decoded offline.
                    </span>
                  </>
                )}
                <input
                  id="image-input"
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
              </label>
              {file && (
                <p className="text-xs text-muted">
                  Selected: <span className="font-medium text-slate-300">{file.name}</span>
                </p>
              )}
            </div>
          )}

          {tab === "camera" && (
            <CameraScanner
              onCapture={({ payload, image_b64 }) =>
                runPipeline({ input_type: "qr_image", image_b64, image_filename: "live-capture.png", text: payload })
              }
            />
          )}

          {tab === "audio" && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    if (recording) {
                      recorder?.stop();
                      return;
                    }
                    try {
                      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                      const mr = new MediaRecorder(stream);
                      const chunks = [];
                      mr.ondataavailable = (e) => chunks.push(e.data);
                      mr.onstop = () => {
                        const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
                        const ext = (mr.mimeType || "audio/webm").includes("ogg") ? "ogg" : "webm";
                        setAudioFile(new File([blob], `voice-note.${ext}`, { type: blob.type }));
                        stream.getTracks().forEach((t) => t.stop());
                        setRecording(false);
                        setRecorder(null);
                      };
                      mr.start();
                      setRecorder(mr);
                      setRecording(true);
                    } catch {
                      setError("Microphone access was blocked — upload an audio file instead.");
                    }
                  }}
                  className={cx(
                    "rounded-full border px-3 py-1.5 font-mono text-[11px] font-bold tracking-wider transition",
                    recording
                      ? "border-neon-red/60 bg-neon-red/20 text-neon-red animate-pulse-glow"
                      : "border-neon-red/40 bg-neon-red/10 text-neon-red hover:bg-neon-red/20"
                  )}
                >
                  {recording ? "⏹ STOP RECORDING" : "🎙 RECORD FROM MICROPHONE"}
                </button>
              {audioFile && (
                <button
                  type="button"
                  onClick={() => setAudioFile(null)}
                  className="rounded-full border border-slate-700 bg-space-900 px-3 py-1.5 font-mono text-[11px] font-bold tracking-wider text-slate-400 hover:text-neon-cyan"
                >
                  ✕ CLEAR CLIP
                </button>
              )}
            </div>

            <AudioWaveform file={audioFile} scanning={submitting} />

            <label
              htmlFor="audio-input"
              className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-space-950/60 p-5 text-center transition hover:border-neon-cyan/50 hover:bg-neon-cyan/5"
            >
              <span className="text-3xl" aria-hidden="true">🎧</span>
              <span className="mt-2 text-sm font-medium text-slate-300">
                {audioFile ? "Replace audio file" : "Click to upload a voicemail / call recording"}
              </span>
              <span className="mt-1 text-xs text-muted">
                .mp3 / .wav / .m4a / .ogg · max 20 MB · analysed locally first, audio never persisted
              </span>
              <input
                id="audio-input"
                type="file"
                accept="audio/*"
                className="sr-only"
                onChange={(event) => setAudioFile(event.target.files?.[0] || null)}
              />
            </label>

            <div>
              <label htmlFor="audio-context" className="sr-only">Context for the analysts (optional)</label>
              <textarea
                id="audio-context"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={3}
                placeholder="Optional context: what did the caller claim? e.g. 'Caller said my son was kidnapped and demanded a wire transfer' — helps the coercion scan."
                className="w-full resize-y rounded-lg border border-slate-700/80 bg-space-950/70 p-3 font-mono text-xs text-slate-200 placeholder:text-faint focus:border-neon-cyan/60 focus:outline-none focus:ring-2 focus:ring-neon-cyan/25"
              />
            </div>
          </div>
        )}
        </div>

        {error && (
          <div role="alert" className="mt-4 rounded-lg border border-neon-red/40 bg-neon-red/10 p-3 text-sm text-red-200">
            <span className="font-bold">SUBMISSION FAILED:</span> {error}
          </div>
        )}

        {submitting ? (
          <div className="mt-5 glass-sub p-4">
            <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center">
              <RadarScan size={180} />
              <ul className="flex-1 space-y-2">
                {PIPELINE_STAGES.map((label, index) => (
                  <li
                    key={label}
                    className={cx(
                      "flex items-center gap-2 font-mono text-[11px] tracking-wider transition",
                      index < stage ? "text-neon-green" : index === stage ? "text-neon-cyan" : "text-faint"
                    )}
                  >
                    <span
                      className={cx(
                        "grid h-4 w-4 place-items-center rounded-full text-[9px] font-bold",
                        index < stage
                          ? "bg-neon-green/20 text-neon-green ring-1 ring-neon-green/50"
                          : index === stage
                          ? "animate-pulse-glow bg-neon-cyan/20 text-neon-cyan ring-1 ring-neon-cyan/60"
                          : "border border-slate-700 text-transparent"
                      )}
                    >
                      ✓
                    </span>
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          tab !== "camera" && (
            <button
              type="submit"
              disabled={!canSubmit}
              className={cx(
                "mt-5 w-full rounded-xl px-4 py-3 font-mono text-sm font-black tracking-[0.18em] transition",
                canSubmit
                  ? "border border-neon-cyan/60 bg-neon-cyan/15 text-neon-cyan shadow-glow-cyan-soft hover:bg-neon-cyan/25"
                  : "cursor-not-allowed border border-slate-700/80 bg-slate-900/60 text-faint"
              )}
            >
              ⚡ INVESTIGATE WITH TRUST//INTERCEPT
            </button>
          )
        )}
      </form>

      {/* Telemetry is secondary to the core decision-defence loop — collapsed. */}
      <LiveMetricsDashboard defaultOpen={false} />

      <p className="mt-4 text-center font-mono text-[11px] tracking-wider text-muted">
        NOTHING IS SENT, BLOCKED, OR FILED AUTOMATICALLY. EVERY ACTION REQUIRES YOUR EXPLICIT APPROVAL.
      </p>
    </div>
  );
}
