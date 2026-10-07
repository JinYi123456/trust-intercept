import { useState } from "react";
import { cx } from "../lib/ui";

/**
 * ReasoningTree — Visual Chain-of-Thought as a cyberpunk vertical timeline.
 * Glowing status nodes (cyan = process step, green = final synthesis) connect
 * through a luminous trace line. Every step is derived from REAL logged
 * evidence entries — nothing is invented for display.
 */

function buildSteps(view) {
  const evidence = view?.evidence || [];
  const byTool = {};
  for (const entry of evidence) {
    if (!byTool[entry.tool]) byTool[entry.tool] = [];
    byTool[entry.tool].push(entry.raw_output);
  }
  const verdict = view?.verdict;
  const steps = [];

  const pii = byTool.pii_redact?.[0];
  const ocr = byTool.ocr?.[0];
  const qr = byTool.qr_decode?.[0];
  const extractDetails = [];
  if (ocr) {
    extractDetails.push(
      `Screenshot transcribed locally via ${ocr.engine}` +
        (ocr.mean_confidence != null ? ` (mean confidence ${ocr.mean_confidence}%)` : "")
    );
  }
  if (qr) {
    extractDetails.push(`QR payload decoded locally via ${qr.engine}; ${qr.urls?.length || 0} URL(s) recovered`);
  }
  extractDetails.push(`${pii?.items_redacted ?? 0} identifier(s) redacted into placeholders pre-analysis`);
  steps.push({ title: "EVIDENCE EXTRACTION & NORMALISATION", body: extractDetails.join(" · ") });

  const router = byTool.router?.[0];
  steps.push({
    title: "ROUTING DECISION",
    body: router
      ? `Modules run: ${router.modules?.join(", ") || "none"} · Deferred (approval-gated): ${
          router.deferred_modules?.join(", ") || "none"
        } · Signals: ${router.signals?.join("; ") || "none"}${router.used_llm ? " · LLM triage consulted" : ""}`
      : "Routing evidence unavailable for this case.",
  });

  const cues = verdict?.cues || [];
  const phishing = byTool.module_1_phishing?.[0];
  const topTypes = [...new Set(cues.map((cue) => cue.cue_type))].slice(0, 4);
  steps.push({
    title: "CUE MATCHING — MODULE 1",
    body: cues.length
      ? `${cues.length} red flag(s) matched against the rule library${
          phishing?.llm_explained ? ", explained in context by the LLM" : " (deterministic explanations)"
        }. Strongest patterns: ${topTypes.join(", ")}`
      : "None of the usual red flags were present in this message.",
  });

  const radar = byTool.psych_radar?.[0];
  if (radar && (radar.vectors || []).length) {
    steps.push({
      title: "PSYCHOLOGICAL MANIPULATION RADAR",
      body: "",
      radar: {
        overall: radar.overall,
        vectors: radar.vectors,
        coolingOff: radar.cooling_off_required,
      },
    });
  }

  const link = byTool.module_2_link_safety?.[0];
  if (link) {
    const hops = (link.chains || []).reduce((sum, chain) => sum + (chain.hops?.length || 0), 0);
    const ages = (link.domains || [])
      .map((intel) =>
        intel.domain_age_days != null ? `${intel.domain}: ${intel.domain_age_days}d old` : `${intel.domain}: age unverifiable`
      )
      .join(" · ");
    steps.push({
      title: "LINK FORENSICS — MODULE 2",
      body: `${(link.chains || []).length} URL(s) · ${hops} hop(s) · ${ages} · ${
        (link.domains || []).some((intel) => (intel.reputation || []).some((rep) => rep.checked && rep.malicious))
          ? "REPUTATION FLAG RAISED"
          : "no reputation flags"
      }`,
    });
  } else {
    steps.push({ title: "LINK FORENSICS — MODULE 2", body: "Skipped — no URL or QR payload in this case." });
  }

  const recon = byTool.sandbox_recon?.[0];
  if (recon) {
    steps.push({
      title: "HONEYPOT SANDBOX RECON — COUNTER-INTEL",
      body: "",
      recon,
    });
  }

  const trace = verdict?.reasoning_trace || {};

  const debate = byTool.agent_debate?.[0];
  if (debate) {
    const lastRound = debate.rounds?.[debate.rounds.length - 1] || {};
    const red = lastRound.red || {};
    const blue = lastRound.blue || {};
    const resolution = debate.resolution || {};
    const topOf = (agent) => (agent.arguments || []).find((item) => item && item.claim) || null;
    steps.push({
      title: "RED TEAM vs BLUE TEAM DEBATE",
      debate: true,
      red: {
        vote: resolution.red_vote || red.score_vote || "—",
        top: topOf(red),
        position: red.position || "scam",
      },
      blue: {
        vote: resolution.blue_vote || blue.score_vote || "—",
        top: topOf(blue),
        position: blue.position || "legitimate",
      },
      consensus: resolution.consensus || "contested",
      rounds: debate.rounds?.length || 0,
      judgeUsed: Boolean(resolution.judge_used),
      policy: resolution.policy || "The debate may raise the risk above the rule floor; it may never lower it.",
    });
  }

  steps.push({
    title: "VERDICT SYNTHESIS",
    body: verdict
      ? `Score ${String(verdict.score).toUpperCase()} · confidence ${verdict.confidence} · ${
          trace.llm_used ? `single LLM call over raw tool outputs (${trace.provider || "provider logged"})` : "deterministic merge of rule outputs (LLM unavailable)"
        }${trace.debate ? ` · Red/Blue debate: ${trace.debate.consensus} over ${trace.debate.rounds} round(s)${trace.debate.judge_used ? " + LLM judge" : ""}` : ""} · prompt, tool outputs and response all logged as evidence.`
      : "No verdict recorded yet.",
    final: true,
  });

  const conflicts = trace.conflicts || [];
  const gaps = trace.gaps || [];
  steps.push({
    title: "UNCERTAINTY CALCULATION",
    body:
      conflicts.length || gaps.length
        ? [...conflicts.map((item) => `CONFLICT: ${item}`), ...gaps.map((item) => `GAP: ${item}`)].join(" · ")
        : verdict?.uncertainty_note
        ? `Note: ${verdict.uncertainty_note}`
        : "No conflicts or gaps — confidence band reflects complete tool coverage.",
  });

  return steps;
}

/**
 * RadarPanel — Psychological Manipulation Radar.
 * Detected cues annotated with named psychological attack vectors and
 * confidence percentages, plus the cooling-off barrier indicator.
 */
function RadarPanel({ radar }) {
  const vectorStyle = (score) =>
    score >= 0.75
      ? "border-neon-red/60 bg-neon-red/10 text-neon-red shadow-glow-red"
      : score >= 0.5
        ? "border-gold-neon/50 bg-gold-neon/10 text-gold-neon shadow-glow-gold-soft"
        : "border-slate-600 bg-slate-800/60 text-slate-400";
  return (
    <div>
      <p className="font-mono text-xs font-bold tracking-[0.16em] text-neon-cyan">
        PSYCHOLOGICAL MANIPULATION RADAR
        <span
          className={cx(
            "ml-2 rounded border px-1.5 py-0.5 font-mono text-[9px] tracking-widest",
            radar.coolingOff ? "border-neon-gold/50 bg-neon-gold/10 text-gold-neon" : "border-slate-700 bg-slate-800/60 text-slate-500"
          )}
        >
          {radar.coolingOff ? "⏸ COOLING-OFF BARRIER REQUIRED" : "NO BARRIER REQUIRED"}
        </span>
      </p>
      <div className="mt-2 space-y-1.5">
        {radar.vectors.map((vector, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className="w-44 shrink-0 truncate font-mono text-[10px] tracking-wider text-slate-400">
              {String(vector.name).replaceAll("_", " ").toUpperCase()}
            </span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-space-800">
              <span
                className={cx(
                  "block h-full rounded-full",
                  vector.score >= 0.75 ? "bg-neon-red shadow-glow-red-soft" : vector.score >= 0.5 ? "bg-gold-neon shadow-glow-gold-soft" : "bg-slate-600"
                )}
                style={{ width: `${Math.round(vector.score * 100)}%` }}
              />
            </span>
            <span className={cx("w-10 shrink-0 text-right font-mono text-[10px] font-bold", vector.score >= 0.75 ? "text-neon-red" : vector.score >= 0.5 ? "text-gold-neon" : "text-slate-500")}>
              {Math.round(vector.score * 100)}%
            </span>
            <span className="hidden w-64 shrink-0 truncate text-[10px] text-slate-600 sm:block" title={vector.basis}>
              {vector.basis}
            </span>
 </div>
        ))}
      </div>
      <p className="mt-2 font-mono text-[9px] leading-relaxed text-slate-600">
        Overall manipulation pressure: {Math.round((radar.overall || 0) * 100)}% · vectors are rule-derived from the matched
        cues and disclosed with their evidence basis.
      </p>
    </div>
  );
}

/**
 * ReconPanel — Honeypot Sandbox Counter-Intel summary.
 * Renders the isolated probe result: C2 IP, host, stack fingerprint, capture
 * list — every field derived from the REAL probe output, never invented.
 */
function ReconPanel({ recon }) {
  const finding = recon.findings || {};
  return (
    <div>
      <p className="font-mono text-xs font-bold tracking-[0.16em] text-neon-cyan">
        HONEYPOT SANDBOX RECON — COUNTER-INTEL
        <span
          className={cx(
            "ml-2 rounded border px-1.5 py-0.5 font-mono text-[9px] tracking-widest",
            recon.status === "completed"
              ? "border-neon-green/50 bg-neon-green/10 text-neon-green"
              : recon.status === "refused"
                ? "border-slate-600 bg-slate-800/60 text-slate-500"
                : "border-gold-neon/50 bg-gold-neon/10 text-gold-neon"
          )}
        >
          {recon.status === "completed" ? "ISOLATED PROBE COMPLETED" : recon.status === "refused" ? "CRITERIA NOT MET" : "PROBE FAILED — NO DATA"}
        </span>
      </p>
      {recon.status === "completed" ? (
        <>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {[
              { label: "C2 / ORIGIN IP", value: finding.ip || "unresolved", cls: "text-neon-red" },
              { label: "HOSTING PROVIDER", value: finding.hosting_provider || "unknown", cls: "text-gold-neon" },
              { label: "TECH STACK FINGERPRINT", value: finding.tech_stack || "unknown", cls: "text-neon-cyan" },
            ].map((cell) => (
              <div key={cell.label} className="glass-sub p-2">
                <p className="font-mono text-[9px] font-bold tracking-[0.18em] text-slate-500">{cell.label}</p>
                <p className={cx("mt-0.5 break-all font-mono text-xs font-bold", cell.cls)}>{cell.value}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 font-mono text-[9px] leading-relaxed text-slate-600">
            Probed {recon.target} · {recon.requests_sent} request(s) · {recon.capture_count || 0} capture command(s) detected
            {recon.ip_source ? ` · IP via ${recon.ip_source}` : ""} · For law-enforcement reporting — never open the link yourself.
          </p>
        </>
      ) : (
        <p className="mt-1 text-xs text-slate-500">{recon.detail || "No sandbox probe was run for this case."}</p>
      )}
    </div>
 );
}

/**
 * DebatePanel — the Red Team vs Blue Team debate visualization.
 * Glowing Cyber Red vs Cyber Blue badges with each side's strongest argument.
 */
function DebatePanel({ step }) {
  const strengthStyle = {
    strong: "border-neon-red/60 bg-neon-red/15 text-neon-red shadow-glow-red",
    high: "border-neon-red/60 bg-neon-red/15 text-neon-red shadow-glow-red",
    moderate: "border-gold-neon/50 bg-gold-neon/10 text-gold-neon shadow-glow-gold-soft",
    medium: "border-gold-neon/50 bg-gold-neon/10 text-gold-neon shadow-glow-gold-soft",
    weak: "border-slate-600 bg-slate-800/60 text-slate-400",
    low: "border-slate-600 bg-slate-800/60 text-slate-400",
  };

  const AgentCard = ({ side, agent }) => (
    <div
      className={cx(
        "glass-sub flex-1 p-3",
        side === "red" ? "border-neon-red/50" : "border-neon-cyan/50"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={cx(
            "rounded border px-2 py-0.5 font-mono text-[10px] font-black tracking-[0.18em]",
            side === "red"
              ? "border-neon-red/60 bg-neon-red/15 text-neon-red shadow-glow-red"
              : "border-neon-cyan/60 bg-neon-cyan/15 text-neon-cyan shadow-glow-cyan"
          )}
        >
          {side === "red" ? "🔴 RED AGENT — PROSECUTION" : "🔵 BLUE AGENT — DEFENCE"}
        </span>
        <span
          className={cx(
            "rounded px-1.5 py-0.5 font-mono text-[10px] font-bold",
            side === "red" ? "bg-neon-red/10 text-neon-red" : "bg-neon-cyan/10 text-neon-cyan"
          )}
        >
          VOTE: {String(agent.vote).toUpperCase()}
        </span>
      </div>
      {agent.top ? (
        <div className="mt-2">
          <p className="text-xs font-semibold leading-snug text-slate-200">{agent.top.claim}</p>
          {agent.top.evidence_quote && (
            <p className="mt-1 break-url font-mono text-[10px] italic text-slate-500">
              “{agent.top.evidence_quote}”
            </p>
          )}
          {agent.top.strength && (
            <span
              className={cx(
                "mt-2 inline-block rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest",
                strengthStyle[agent.top.strength] || strengthStyle.weak
              )}
            >
              {String(agent.top.technique || "signal").replaceAll("_", " ").toUpperCase()} · {String(agent.top.strength).toUpperCase()}
            </span>
          )}
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-500">No argument recorded for this side.</p>
      )}
    </div>
  );

  return (
    <div>
      <p className="font-mono text-xs font-bold tracking-[0.16em] text-slate-200">
        RED TEAM <span className="text-neon-red">vs</span> BLUE TEAM DEBATE
        <span className="ml-2 rounded border border-neon-cyan/40 bg-neon-cyan/10 px-1.5 py-0.5 font-mono text-[9px] tracking-widest text-neon-cyan">
          {step.rounds} ROUND{step.rounds === 1 ? "" : "S"}
          {step.judgeUsed ? " · LLM JUDGE" : " · DETERMINISTIC"}
        </span>
      </p>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <AgentCard side="red" agent={step.red} />
        <AgentCard side="blue" agent={step.blue} />
      </div>
      <p className="mt-2 font-mono text-[10px] leading-relaxed text-slate-500">
        CONSENSUS: <span className="text-slate-300">{String(step.consensus).replaceAll("_", " ").toUpperCase()}</span> · {step.policy}
      </p>
    </div>
  );
}

export default function ReasoningTree({ view }) {
  const [open, setOpen] = useState(true);
  const steps = buildSteps(view);

  return (
    <section className="glass-panel p-4 sm:p-6">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={open}
      >
        <span>
          <span className="label-cyber block text-neon-cyan">AGENT THOUGHT PROCESS — VISUAL CHAIN OF THOUGHT</span>
          <span className="mt-0.5 block text-xs text-slate-500">
            Reconstructed from the logged evidence trail; nothing is invented.
          </span>
        </span>
        <span className="font-mono text-neon-cyan">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <ol className="relative mt-5 space-y-0 pl-1">
          {/* luminous trace line */}
          <span aria-hidden="true" className="absolute bottom-3 left-[13px] top-3 w-px bg-gradient-to-b from-neon-cyan/60 via-neon-cyan/20 to-neon-green/50" />
          {steps.map((step, index) => (
            <li key={step.title} className="relative flex gap-4 pb-5 last:pb-0">
              <span
                aria-hidden="true"
                className={cx(
                  "z-10 mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full font-mono text-[10px] font-bold ring-2",
                  step.final
                    ? "bg-neon-green/15 text-neon-green ring-neon-green/60 shadow-glow-green"
                    : step.debate
                    ? "bg-space-800 text-slate-100 ring-slate-400/60"
                    : "bg-space-800 text-neon-cyan ring-neon-cyan/50 shadow-glow-cyan-soft"
                )}
              >
                {step.debate ? "⚔" : String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0">
                {step.debate ? (
                  <DebatePanel step={step} />
                ) : step.radar ? (
                  <RadarPanel radar={step.radar} />
                ) : step.recon ? (
                  <ReconPanel recon={step.recon} />
                ) : (
                  <>
                    <p className={cx("font-mono text-xs font-bold tracking-[0.16em]", step.final ? "text-neon-green" : "text-neon-cyan")}>
                      {step.title}
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-400">{step.body}</p>
                  </>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
