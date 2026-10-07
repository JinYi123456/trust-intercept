/**
 * RadarScan — the "active defence" radar shown while TRUST//INTERCEPT investigates.
 * Pure CSS/SVG: concentric range rings, a rotating neon sweep, contact blips,
 * and a vertical cyber scan-line over the whole panel.
 */
export default function RadarScan({ label = "ACTIVE DEFENCE SWEEP", size = 220 }) {
  const rings = [0.32, 0.56, 0.8, 1];
  const blips = [
    { x: "30%", y: "38%", delay: "0s" },
    { x: "68%", y: "30%", delay: ".6s" },
    { x: "58%", y: "70%", delay: "1.1s" },
    { x: "36%", y: "66%", delay: "1.5s" },
  ];

  return (
    <div className="flex flex-col items-center">
      <div
        className="relative rounded-full border border-neon-cyan/25 bg-slate-950/60 shadow-glow-cyan-soft"
        style={{ width: size, height: size }}
        role="img"
        aria-label="Radar animation: TRUST//INTERCEPT is actively scanning the artefact"
      >
        {/* range rings + crosshairs */}
        {rings.map((r) => (
          <span
            key={r}
            className="absolute rounded-full border border-neon-cyan/15"
            style={{
              inset: `${((1 - r) / 2) * 100}%`,
            }}
          />
        ))}
        <span className="absolute left-1/2 top-0 h-full w-px bg-neon-cyan/10" />
        <span className="absolute top-1/2 left-0 w-full h-px bg-neon-cyan/10" />

        {/* rotating sweep */}
        <div
          className="absolute inset-0 rounded-full animate-radar-sweep"
          style={{
            background:
              "conic-gradient(from 0deg, rgba(0,229,255,0) 0deg, rgba(0,229,255,.28) 55deg, rgba(0,229,255,.55) 62deg, transparent 64deg)",
          }}
        />

        {/* contact blips */}
        {blips.map((blip, i) => (
          <span
            key={i}
            className="absolute h-1.5 w-1.5 rounded-full bg-neon-green shadow-glow-green animate-blip"
            style={{ left: blip.x, top: blip.y, animationDelay: blip.delay }}
          />
        ))}

        {/* centre dot */}
        <span className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-neon-cyan shadow-glow-cyan" />
      </div>

      <p className="mt-4 font-mono text-[11px] tracking-[0.3em] text-neon-cyan/90 animate-pulse-glow">
        {label}
      </p>
    </div>
  );
}
