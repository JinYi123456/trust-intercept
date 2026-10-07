import { cx } from "../lib/ui";

/**
 * ThreatGauge — prominent severity gauge + alert banner (replaces plain badges).
 * Semi-circular SVG gauge with a neon arc whose colour/glow encodes the score;
 * the banner beneath carries the pulsing status dot and the confidence band.
 */

const SCORES = {
  low: { label: "SAFE", angle: -80, color: "#00E676", glow: "shadow-glow-green", text: "text-neon-green", ring: "ring-neon-green/40", bg: "bg-neon-green/10" },
  medium: { label: "REVIEW", angle: 0, color: "#FFB800", glow: "shadow-glow-gold", text: "text-neon-gold", ring: "ring-neon-gold/40", bg: "bg-neon-gold/10" },
  high: { label: "HIGH RISK", angle: 80, color: "#FF0055", glow: "shadow-glow-red", text: "text-neon-red", ring: "ring-neon-red/50", bg: "bg-neon-red/10" },
};

const ARC_RADIUS = 78;
const CENTER = 100;

function polar(angleDeg, radius = ARC_RADIUS) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: CENTER + radius * Math.cos(rad), y: CENTER + radius * Math.sin(rad) };
}

function arcPath(fromAngle, toAngle) {
  const start = polar(fromAngle);
  const end = polar(toAngle);
  return `M ${start.x} ${start.y} A ${ARC_RADIUS} ${ARC_RADIUS} 0 0 1 ${end.x} ${end.y}`;
}

export default function ThreatGauge({ score = "low", confidence, actionRequired }) {
  const config = SCORES[String(score).toLowerCase()] || SCORES.low;
  const needle = polar(config.angle, 58);
  const filled = arcPath(-80, config.angle);

  return (
    <div className="glass-panel overflow-hidden">
      {/* Alert banner */}
      <div
        className={cx(
          "flex items-center gap-3 px-4 py-3 border-b border-slate-800/80",
          config.bg
        )}
      >
        <span
          className={cx(
            "h-3 w-3 shrink-0 rounded-full animate-pulse-glow",
            score === "high" ? "bg-neon-red shadow-glow-red" : score === "medium" ? "bg-neon-gold shadow-glow-gold" : "bg-neon-green shadow-glow-green"
          )}
        />
        <p className={cx("font-mono text-sm font-bold tracking-[0.22em]", config.text)}>
          {score === "high" ? "⚠ THREAT ALERT" : score === "medium" ? "◑ MANUAL REVIEW ADVISED" : "✓ NO ACTIVE THREAT DETECTED"}
        </p>
        {actionRequired && (
          <span className="ml-auto hidden rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-widest text-neon-cyan sm:inline">
            ACTION REQUIRED
          </span>
        )}
      </div>

      {/* Gauge + readout */}
      <div className="flex flex-col items-center gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-center sm:gap-10">
        <div className="relative" style={{ width: 200, height: 118 }}>
          <svg viewBox="0 0 200 118" className="h-full w-full">
            {/* track */}
            <path d={arcPath(-80, 80)} fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="round" />
            {/* tick marks */}
            {[-80, -40, 0, 40, 80].map((angle) => {
              const a = polar(angle, 94);
              const b = polar(angle, 102);
              return (
                <line key={angle} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke="#334155" strokeWidth="2" strokeLinecap="round" />
              );
            })}
            {/* filled arc */}
            <path d={filled} fill="none" stroke={config.color} strokeWidth="14" strokeLinecap="round"
              style={{ filter: `drop-shadow(0 0 8px ${config.color}) drop-shadow(0 0 22px ${config.color}55)` }} />
            {/* needle */}
            <line x1={CENTER} y1={CENTER} x2={needle.x} y2={needle.y}
              stroke={config.color} strokeWidth="3.5" strokeLinecap="round"
              style={{ filter: `drop-shadow(0 0 6px ${config.color})` }} />
            <circle cx={CENTER} cy={CENTER} r="7" fill="#0D1322" stroke={config.color} strokeWidth="2.5" />
          </svg>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 text-center">
            <span className={cx("font-mono text-2xl font-black tracking-[0.14em]", config.text)}
              style={{ textShadow: `0 0 14px ${config.color}88` }}>
              {config.label}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 font-mono text-xs sm:grid-cols-1">
          <div className="glass-sub px-3 py-2">
            <span className="block text-slate-500">CONFIDENCE BAND</span>
            <span className={cx("text-sm font-bold", config.text)}>
              {String(confidence || "—").toUpperCase()}
            </span>
          </div>
          <div className="glass-sub px-3 py-2">
            <span className="block text-slate-500">MODE</span>
            <span className="text-sm font-bold text-slate-200">
              {actionRequired ? "DEFEND" : "MONITOR"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
