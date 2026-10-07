import { useCallback, useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { cx } from "../lib/ui";

/**
 * CameraScanner — live QR capture with the device camera.
 *
 * Uses navigator.mediaDevices.getUserMedia to stream video, samples frames to
 * a hidden canvas, and decodes each frame locally with jsQR (no cloud, no
 * upload). On detection the payload is previewed; "Analyse" hands the captured
 * frame to the TRUST//INTERCEPT pipeline as a qr_image case.
 */
export default function CameraScanner({ onCapture }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const loopRef = useRef(null);
  const [status, setStatus] = useState("idle"); // idle | starting | scanning | detected | error
  const [error, setError] = useState("");
  const [payload, setPayload] = useState("");

  const stopEverything = useCallback(() => {
    if (loopRef.current) {
      clearInterval(loopRef.current);
      loopRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => stopEverything, [stopEverything]);

  const start = useCallback(async () => {
    setError("");
    setPayload("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setError(
        "This browser does not expose a camera API (or the page is not served over HTTPS/localhost). Use the Screenshot / QR upload tab instead."
      );
      return;
    }
    setStatus("starting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      video.srcObject = stream;
      await video.play();
      setStatus("scanning");

      const canvas = canvasRef.current;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      loopRef.current = setInterval(() => {
        if (!video.videoWidth) return;
        const w = 480;
        const h = Math.round((video.videoHeight / video.videoWidth) * w);
        canvas.width = w;
        canvas.height = h;
        context.drawImage(video, 0, 0, w, h);
        const imageData = context.getImageData(0, 0, w, h);
        const code = jsQR(imageData.data, w, h, { inversionAttempts: "attemptBoth" });
        if (code && code.data && code.data.trim()) {
          setPayload(code.data.trim());
          setStatus("detected");
          stopEverything();
        }
      }, 350);
    } catch (cameraError) {
      setStatus("error");
      const name = cameraError?.name || "";
      setError(
        name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access for this site, or use the Screenshot / QR upload tab."
          : name === "NotFoundError"
          ? "No camera device was found on this system."
          : `Camera unavailable (${name || "unknown error"}). Use the Screenshot / QR upload tab instead — it works fully offline.`
      );
    }
  }, [stopEverything]);

  function analyse() {
    if (!payload) return;
    const canvas = canvasRef.current;
    let image_b64 = "";
    if (canvas && canvas.width) {
      image_b64 = canvas.toDataURL("image/png").split(",")[1] || "";
    }
    onCapture({ payload, image_b64 });
  }

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-xl border border-neon-cyan/30 bg-black/60 shadow-glow-cyan-soft">
        {/* live video feed */}
        <video
          ref={videoRef}
          playsInline
          muted
          className={cx(
            "block aspect-[4/3] w-full object-cover",
            status === "scanning" || status === "detected" ? "opacity-100" : "opacity-0"
          )}
        />
        {/* decoder canvas (hidden) */}
        <canvas ref={canvasRef} className="hidden" />

        {status !== "scanning" && status !== "detected" && (
          <div className="absolute inset-0 grid place-items-center bg-space-850/80 p-6 text-center">
            <div>
              <p className="text-4xl" aria-hidden="true">📷</p>
              <p className="mt-3 text-sm text-slate-300">
                {status === "starting"
                  ? "Requesting camera access…"
                  : status === "error"
                  ? "Camera unavailable"
                  : "Camera feed idle"}
              </p>
            </div>
          </div>
        )}

        {/* targeting reticle + scan line */}
        {(status === "scanning" || status === "detected") && (
          <>
            <div className="pointer-events-none absolute inset-8 rounded-lg border-2 border-neon-cyan/70 shadow-glow-cyan" />
            <div className="pointer-events-none absolute inset-8 overflow-hidden rounded-lg">
              <div className="absolute left-0 h-0.5 w-full bg-neon-cyan shadow-glow-cyan animate-scan-y" />
            </div>
            {status === "scanning" && (
              <p className="absolute inset-x-0 bottom-3 text-center font-mono text-[11px] tracking-[0.25em] text-neon-cyan">
                SCANNING FOR QR PAYLOAD…
              </p>
            )}
          </>
        )}

        {status === "detected" && (
          <div className="absolute inset-x-0 top-0 bg-neon-green/15 px-4 py-2 text-center font-mono text-[11px] font-bold tracking-[0.25em] text-neon-green">
            ✓ QR PAYLOAD CAPTURED — DECODED LOCALLY
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-neon-red/40 bg-neon-red/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {status === "detected" && (
        <div className="glass-sub p-3">
          <p className="label-cyber">Decoded payload</p>
          <p className="mt-1 break-url font-mono text-sm text-neon-green">{payload}</p>
        </div>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        {(status === "idle" || status === "error") && (
          <button type="button" onClick={start} className="btn-cyber flex-1 border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/20">
            ▶ Start live camera scan
          </button>
        )}
        {status === "scanning" && (
          <button type="button" onClick={stopEverything} className="btn-cyber flex-1 border-slate-700 bg-slate-800/60 text-slate-300 hover:bg-slate-700/60">
            ■ Stop camera
          </button>
        )}
        {status === "detected" && (
          <>
            <button type="button" onClick={analyse} className="btn-cyber flex-1 border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan shadow-glow-cyan-soft hover:bg-neon-cyan/20">
              ⚡ Analyse this QR with TRUST//INTERCEPT
            </button>
            <button type="button" onClick={start} className="btn-cyber border-slate-700 bg-slate-800/60 text-slate-300 hover:bg-slate-700/60">
              ↻ Rescan
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-slate-500">
        Frames are decoded <strong className="text-slate-400">on-device</strong> with jsQR — the
        video stream never leaves your machine. Only the captured frame you approve is sent to
        the TRUST//INTERCEPT pipeline for link forensics.
      </p>
    </div>
  );
}
