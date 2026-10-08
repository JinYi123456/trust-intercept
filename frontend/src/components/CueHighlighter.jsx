import { cx, severityDotClass } from "../lib/ui";

/**
 * CueHighlighter — renders the (PII-redacted) message with each manipulative
 * phrase wrapped in a glowing neon tag. Hovering (or focusing) a tag pops an
 * explanation card stating the matched rule and WHY it is a red flag. If no
 * cues were found, it says so explicitly — never a bare "safe".
 */

function severityStyle(severity) {
  switch (String(severity || "").toLowerCase()) {
    case "high":
      return "border-neon-red/70 bg-neon-red/10 text-red-100 shadow-glow-red";
    case "medium":
      return "border-neon-gold/60 bg-neon-gold/10 text-amber-100 shadow-glow-gold";
    default:
      return "border-neon-cyan/50 bg-neon-cyan/10 text-cyan-100 shadow-glow-cyan-soft";
  }
}

function buildSegments(text, cues) {
  const lower = text.toLowerCase();
  const matches = [];

  (cues || []).forEach((cue, cueIndex) => {
    const quote = String(cue?.text || "").trim();
    if (!quote) return;
    const start = lower.indexOf(quote.toLowerCase());
    if (start === -1) return;
    matches.push({ start, end: start + quote.length, cueIndex });
  });

  matches.sort((a, b) => a.start - b.start || b.end - a.end);

  const picked = [];
  let lastEnd = -1;
  for (const match of matches) {
    if (match.start >= lastEnd) {
      picked.push(match);
      lastEnd = match.end;
    }
  }

  const segments = [];
  let cursor = 0;
  for (const match of picked) {
    if (match.start > cursor) {
      segments.push({ text: text.slice(cursor, match.start), isCue: false });
    }
    segments.push({ text: text.slice(match.start, match.end), isCue: true, cueIndex: match.cueIndex });
    cursor = match.end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), isCue: false });
  }
  return segments;
}

function CuePopover({ cue, index }) {
  return (
    <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden w-64 -translate-x-1/2 group-hover:block group-focus-within:block">
      <span className="glass-panel block border-neon-red/40 p-3 text-left shadow-glow-red">
        <span className="flex items-center gap-2">
          <span
            className={cx("h-2 w-2 rounded-full", severityDotClass(cue.severity))}
            aria-hidden="true"
          />
          <span className="sr-only">{String(cue.severity || "low").toUpperCase()} severity</span>
          <span aria-hidden="true" className="text-xs">
            {String(cue.severity).toLowerCase() === "high" ? "⛔" : String(cue.severity).toLowerCase() === "medium" ? "⚠️" : "•"}
          </span>
          <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-widest text-slate-300">
            {String(cue.cue_type || "cue").toUpperCase()}
          </span>
          <span className="font-mono text-[10px] text-muted">
            {cue.source === "llm" ? "LLM-EXPLAINED" : "RULE MATCH"}
          </span>
        </span>
        <span className="mt-1.5 block text-xs leading-relaxed text-slate-200">
          {cue.explanation}
        </span>
        <span className="mt-1.5 block font-mono text-[10px] tracking-widest text-muted">
          SEVERITY: {String(cue.severity || "—").toUpperCase()}
        </span>
      </span>
    </span>
  );
}

export default function CueHighlighter({ text = "", cues = [] }) {
  if (!text || !text.trim()) {
    return (
      <p className="glass-sub p-4 text-sm text-muted">
        No message text is available for this case.
      </p>
    );
  }

  const segments = buildSegments(text, cues);

  return (
    <div>
      <div className="whitespace-pre-wrap rounded-lg border border-slate-800/80 bg-space-950/70 p-4 font-mono text-sm leading-loose text-slate-300 sm:text-[15px]">
        {segments.map((segment, index) =>
          segment.isCue ? (
            <span key={index} className="group relative inline-block">
              <span
                tabIndex={0}
                title={cues[segment.cueIndex]?.explanation || "Flagged as suspicious"}
                className={cx(
                  "cursor-help rounded border px-1 py-0.5 font-semibold outline-none transition",
                  severityStyle(cues[segment.cueIndex]?.severity)
                )}
              >
                {segment.text}
                <sup className="ml-0.5 rounded-full bg-slate-950/80 px-1 font-mono text-[10px] font-bold text-neon-red">
                  {segment.cueIndex + 1}
                </sup>
              </span>
              <CuePopover cue={cues[segment.cueIndex]} index={segment.cueIndex} />
            </span>
          ) : (
            <span key={index}>{segment.text}</span>
          )
        )}
      </div>

      <ol className="mt-4 space-y-3">
        {cues.map((cue, index) => (
          <li key={index} className="glass-sub flex gap-3 p-3">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-neon-red/20 font-mono text-xs font-bold text-neon-red ring-1 ring-neon-red/50">
              {index + 1}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cx("h-2.5 w-2.5 shrink-0 rounded-full", severityDotClass(cue.severity))}
                  aria-hidden="true"
                />
                <span className="sr-only">{String(cue.severity || "low").toUpperCase()} severity</span>
                <span aria-hidden="true" className="text-xs">
                  {String(cue.severity).toLowerCase() === "high" ? "⛔" : String(cue.severity).toLowerCase() === "medium" ? "⚠️" : "•"}
                </span>
                <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[11px] font-semibold tracking-wider text-slate-300">
                  {cue.cue_type || "cue"}
                </span>
                <span className="font-mono text-[10px] tracking-widest text-muted">
                  {cue.source === "llm" ? "LLM-EXPLAINED" : "RULE MATCH"}
                </span>
              </div>
              <p className="mt-1 break-url text-xs text-muted">“{cue.text}”</p>
              <p className="mt-1 text-sm text-slate-300">{cue.explanation}</p>
            </div>
          </li>
        ))}
      </ol>

      {cues.length === 0 && (
        <div className="mt-4 rounded-lg border border-neon-green/40 bg-neon-green/10 p-4 text-sm text-neon-green shadow-glow-green">
          ✓ None of the usual red flags were present in this message — no urgency pressure, no
          credential or OTP requests, no payment demands, and no disguised links.
        </div>
      )}
    </div>
  );
}
