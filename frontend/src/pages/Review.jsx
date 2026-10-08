import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client.js";
import AuditLog from "../components/AuditLog.jsx";
import CueHighlighter from "../components/CueHighlighter.jsx";
import ReasoningTree from "../components/ReasoningTree.jsx";
import RedirectChain from "../components/RedirectChain.jsx";
import ThreatGauge from "../components/ThreatGauge.jsx";
import VoiceExplanation from "../components/VoiceExplanation.jsx";
import EvidencePassport from "../components/EvidencePassport.jsx";
import ManipulationGraph from "../components/ManipulationGraph.jsx";
import EvidenceChallengeMatrix from "../components/EvidenceChallengeMatrix.jsx";
import CounterfactualVerification from "../components/CounterfactualVerification.jsx";
import CaseReplay from "../components/CaseReplay.jsx";
import { ACTION_LABELS, cx, formatDateTime } from "../lib/ui";

/**
 * Review — the central Human Review screen (Framework section 05).
 *
 * The verdict, evidence, and proposed action are shown on ONE screen, and
 * nothing irreversible happens without a click: "Looks Safe", "Report This",
 * "Block/Warn", or "I disagree, re-check". The buttons POST to
 * /case/{id}/decision — the ONLY endpoint in the backend that can write
 * action_taken (the structural human-approval gate).
 *
 * Tabs:
 *  - "Verdict & Evidence": threat gauge, voice explanation, reasoning tree,
 *    cues, redirect chains, decision buttons, reasoning trace.
 *  - "Audit Log": the client-side audit-trail dashboard (timestamps, risk
 *    deltas, SHA-256 verification hashes) for compliance.
 */

const DECISION_BUTTONS = [
  {
    action: "looks_safe",
    label: "Looks Safe",
    className: "gate-btn gate-safe",
    hint: "Dismiss this case. Nothing was blocked or sent.",
  },
  {
    action: "report",
    label: "Report This",
    className: "gate-btn gate-report",
    hint: "Generate the PII-redacted report bundle. You send it.",
  },
  {
    action: "block_warn",
    label: "Block / Warn",
    className: "gate-btn gate-warn",
    hint: "Show a plain-language warning with the specific reasons.",
  },
  {
    action: "disagree_recheck",
    label: "I Disagree, Re-check",
    className: "gate-btn gate-disagree",
    hint: "Re-run the investigation with your correction noted.",
  },
];

const TABS = [
  { id: "verdict", label: "VERDICT & EVIDENCE" },
  { id: "audit", label: "AUDIT LOG" },
];

function buildVoiceScript(verdict, cueLimit = 4) {
  if (!verdict) return "";
  const parts = [`TRUST//INTERCEPT verdict. Risk level ${verdict.score}, with ${verdict.confidence} confidence.`];
  if (verdict.summary) parts.push(verdict.summary);
  const cues = verdict.cues || [];
  if (cues.length) {
    parts.push(`${cues.length} red flag${cues.length === 1 ? "" : "s"} were found.`);
    cues.slice(0, cueLimit).forEach((cue, index) => {
      parts.push(`Red flag ${index + 1}, ${cue.cue_type.replace(/_/g, " ")}: ${cue.explanation}`);
    });
  } else {
    parts.push("None of the usual red flags were present in this message.");
  }
  if (verdict.uncertainty_note) parts.push(`Please note: ${verdict.uncertainty_note}`);
  parts.push(
    "Remember: TRUST//INTERCEPT investigates and explains. The person decides. Nothing was blocked, sent, or filed."
  );
  return parts.join(" ");
}

function PanelTitle({ children }) {
  return (
    <h2 className="flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
      <span className="h-px flex-1 bg-gradient-to-r from-transparent via-neon-cyan/40 to-transparent" />
      {children}
    </h2>
  );
}

export default function Review() {
  const { caseId } = useParams();
  const [view, setView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("verdict");

  const [pendingAction, setPendingAction] = useState(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection] = useState("");
  const [warningShown, setWarningShown] = useState(null);
  const [safeConfirmed, setSafeConfirmed] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [coolingOff, setCoolingOff] = useState(0); // seconds remaining on the barrier
  const [coolingAction, setCoolingAction] = useState(null);
  const [recon, setRecon] = useState(null);
  const [reconBusy, setReconBusy] = useState(false);
  const [muted, setMuted] = useState(false);
  const alertFiredRef = useRef(false);
  const [caregiverHash, setCaregiverHash] = useState("");

  // Derived early: the caregiver block and the gate both need these.
  const verdict = view?.verdict;
  const caseInfo = view?.case || {};
  const radarEvidence = (view?.evidence || []).find((entry) => entry.tool === "psych_radar")?.raw_output || null;
  const defenceEvidence = (view?.evidence || []).find((entry) => entry.tool === "decision_defence")?.raw_output || null;
  const verificationEvidence = (view?.evidence || []).find((entry) => entry.tool === "counterfactual_verification")?.raw_output || null;
  const coolingRequired = Boolean(radarEvidence?.cooling_off_required);

  // --- Trusted Caregiver Safety Circle -------------------------------------
  // Shown only when the verdict is HIGH and manipulation pressure exceeds
  // 75%. The alert text is pre-formatted and PII-SAFE by construction: it
  // contains the case id, risk level, redacted cue quotes, and a client-side
  // SHA-256 evidence hash — never the original message or any identifier.
  const caregiverEligible =
    verdict?.score === "high" && Number(radarEvidence?.overall || 0) > 0.75;

  useEffect(() => {
    if (!caregiverEligible || !view?.case) {
      setCaregiverHash("");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const bytes = new TextEncoder().encode(
          `${view.case.id}|${verdict.score}|${view.case.redacted_text}`
        );
        const digest = await crypto.subtle.digest("SHA-256", bytes);
        const hex = Array.from(new Uint8Array(digest))
          .map((byte) => byte.toString(16).padStart(2, "0"))
          .join("");
        if (!cancelled) setCaregiverHash(hex);
      } catch {
        if (!cancelled) setCaregiverHash("unavailable-offline");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caregiverEligible, view?.case, verdict?.score]);

  const topCuesForCircle = (verdict?.cues || [])
    .filter((cue) => cue.severity === "high")
    .slice(0, 3);
  const caregiverMessage = caregiverEligible
    ? [
        "🛡 TRUST//INTERCEPT SAFETY CIRCLE ALERT",
        "",
        `A message was just analysed with TRUST//INTERCEPT and scored HIGH risk.`,
        `Case: ${view?.case?.id || "—"}`,
        `Risk: HIGH · manipulation pressure ${Math.round((radarEvidence?.overall || 0) * 100)}%`,
        "",
        "Top red flags (redacted quotes):",
        ...topCuesForCircle.map(
          (cue) => `• ${cue.cue_type}: "${cue.text}"`
        ),
        "",
        `Evidence hash (SHA-256): ${caregiverHash || "computing…"}`,
        "Verified locally by TRUST//INTERCEPT — this alert contains NO personal data.",
        "Please check in with your family member.",
      ].join("\n")
    : "";
  const circleLinks = caregiverMessage
    ? [
        { label: "✈ TELEGRAM", href: `https://t.me/share/url?url=${encodeURIComponent(" ")}&text=${encodeURIComponent(caregiverMessage)}` },
        { label: "💬 WHATSAPP", href: `https://wa.me/?text=${encodeURIComponent(caregiverMessage)}` },
        { label: "✉ EMAIL", href: `mailto:?subject=${encodeURIComponent("TRUST//INTERCEPT Safety Circle Alert — HIGH risk")}&body=${encodeURIComponent(caregiverMessage)}` },
      ]
    : [];

  // Hardware feedback — synthesized Web Audio pulse + haptic vibration on a
  // HIGH-risk verdict. Zero external assets: the tone is generated with an
  // OscillatorNode; vibration uses the Vibration API where available. Fires
  // once per case load, respects the mute toggle, and never throws.
  useEffect(() => {
    if (!view?.verdict || alertFiredRef.current) return;
    alertFiredRef.current = true;
    if (view.verdict.score !== "high" || muted) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const context = new AudioCtx();
        const pulse = (startDelay, frequency) => {
          const oscillator = context.createOscillator();
          const gain = context.createGain();
          oscillator.type = "sine";
          oscillator.frequency.value = frequency;
          gain.gain.setValueAtTime(0.0001, context.currentTime + startDelay);
          gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + startDelay + 0.03);
          gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + startDelay + 0.22);
          oscillator.connect(gain).connect(context.destination);
          oscillator.start(context.currentTime + startDelay);
          oscillator.stop(context.currentTime + startDelay + 0.25);
        };
        pulse(0, 880); // rising two-tone cyber alert
        pulse(0.28, 660);
        setTimeout(() => context.close(), 1000);
      }
      if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
        navigator.vibrate([100, 50, 100]);
      }
    } catch {
      /* hardware feedback is best-effort only */
    }
  }, [view?.verdict, muted]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.getCase(caseId);
      setView(data);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDecision(action, { skipCooling = false } = {}) {
    if (action === "disagree_recheck" && !showCorrection) {
      setShowCorrection(true);
      return;
    }
    // Psychological Shield: a 10-second cooling-off barrier before HIGH-RISK
    // actions when the manipulation radar crosses its threshold. Deliberate
    // friction against urgency-based scams — the countdown runs in the UI and
    // can be cancelled. It NEVER applies to "Looks Safe" (protecting a
    // clean case from friction) and never blocks re-checks mid-count.
    if (
      coolingRequired &&
      !skipCooling &&
      (action === "report" || action === "block_warn") &&
      coolingOff === 0 &&
      coolingAction !== action
    ) {
      setCoolingAction(action);
      setCoolingOff(10);
      return;
    }
    setPendingAction(action);
    setError(null);
    try {
      const body = { human_action: action, decided_by: "user" };
      if (action === "disagree_recheck") {
        body.correction = correction.trim();
        if (!body.correction) {
          setError("Please describe what you disagree with so TRUST//INTERCEPT can re-check.");
          setPendingAction(null);
          return;
        }
      }
      const updated = await api.postDecision(caseId, body);
      setView(updated);

      const latest = (updated.decisions || [])[(updated.decisions || []).length - 1];
      if (action === "block_warn") setWarningShown(latest?.action_taken || "Warning shown.");
      if (action === "looks_safe") setSafeConfirmed(true);
      if (action === "disagree_recheck") {
        setShowCorrection(false);
        setCorrection("");
      }
      if (action === "report") {
        window.location.assign(`/case/${caseId}/report`);
        return;
      }
    } catch (decisionError) {
      setError(decisionError.message);
    } finally {
      setPendingAction(null);
    }
  }

  // Cooling-off countdown driver (Psychological Shield).
  useEffect(() => {
    if (coolingOff <= 0) return undefined;
    const timer = setTimeout(() => setCoolingOff((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [coolingOff]);

  async function handleRecon() {
    setReconBusy(true);
    setError(null);
    try {
      const result = await api.runSandboxRecon(caseId);
      setRecon(result);
      const refreshed = await api.getCase(caseId);
      setView(refreshed);
    } catch (reconError) {
      setError(reconError.message);
    } finally {
      setReconBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-pulse-glow font-mono text-xs tracking-[0.3em] text-neon-cyan">
          LOADING CASE FORENSICS…
        </div>
      </div>
    );
  }

  if (error && !view) {
    return (
      <div className="mx-auto max-w-3xl">
        <div role="alert" className="glass-panel border-neon-red/40 p-4 text-sm text-red-200">{error}</div>
        <Link to="/" className="mt-4 inline-block font-mono text-xs tracking-wider text-neon-cyan hover:underline">
          ← BACK TO SUBMISSION
        </Link>
      </div>
    );
  }

  const decisions = view?.decisions || [];
  const cues = verdict?.cues || [];

  // Module 2 artefacts are stored as evidence entries by the orchestrator.
  const linkEvidence = (view?.evidence || []).filter(
    (entry) => entry.tool === "module_2_link_safety"
  );
  const chains = linkEvidence.flatMap((entry) => entry.raw_output?.chains || []);
  const domains = linkEvidence.flatMap((entry) => entry.raw_output?.domains || []);

  const notChecked = [
    ...(caseInfo.normalisation_notes || []),
    "TRUST//INTERCEPT reasons over patterns and public reputation data — it cannot verify a caller's or sender's real-world identity.",
  ];

  const debateEvidence = (view?.evidence || []).find((entry) => entry.tool === "agent_debate")?.raw_output || null;
  const debateRound = debateEvidence?.rounds?.[debateEvidence.rounds.length - 1] || null;
  const debateResolution = debateEvidence?.resolution || null;
  const evidenceTimeline = (view?.evidence || []).map((entry, index) => ({
    index: index + 1,
    tool: entry.tool,
    time: entry.collected_at,
    state: entry.raw_output?.module_failed ? "FAILED / FALLBACK" : "CAPTURED",
  }));

  const agentRows = [
    { name: "HUNTER", role: "attack evidence", state: verdict ? "COMPLETE" : "QUEUED", mark: "01" },
    { name: "SKEPTIC", role: "false-positive challenge", state: verdict ? "COMPLETE" : "QUEUED", mark: "02" },
    { name: "VERIFIER", role: "decision-changing evidence", state: defenceEvidence ? "COMPLETE" : "QUEUED", mark: "03" },
    { name: "ARBITER", role: "evidence synthesis", state: verdict ? "COMPLETE" : "QUEUED", mark: "04" },
  ];
  const intendedAction =
    defenceEvidence?.attacker_intended_action ||
    defenceEvidence?.intended_action ||
    defenceEvidence?.attack_chain?.nodes?.find((node) => node.kind === "action")?.label ||
    (verdict?.action_required ? verdict.action_required.replaceAll("_", " ") : "—");

  return (
    <div className="mx-auto max-w-7xl">
      {/* Case header + tabs */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="font-mono text-lg font-black uppercase tracking-[0.2em] text-slate-200 sm:text-xl">
          <span className="neon-cyan-text">INTERCEPTION</span> ROOM
        </h1>
        <span className="glass-sub rounded-full px-3 py-1 font-mono text-[11px] tracking-wider text-slate-400">
          CASE <span className="text-neon-cyan">{caseId}</span> · {caseInfo.input_type} · {caseInfo.status}
        </span>
      </div>

      <section className="intercept-hero mb-5 overflow-hidden rounded-2xl border border-slate-800/90">
        <div className="intercept-hero-grid">
          <div className="p-5 sm:p-6 lg:p-7">
            <div className="flex flex-wrap items-center gap-2">
              <span className="status-dot" />
              <span className="font-mono text-[10px] font-bold tracking-[0.24em] text-neon-cyan">LIVE EVIDENCE OBSERVATORY</span>
              <span className="rounded-full border border-slate-700 bg-slate-950/60 px-2 py-1 font-mono text-[9px] tracking-wider text-slate-500">HUMAN-GATED</span>
            </div>
            <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
              <div>
                <p className="font-mono text-[10px] tracking-[0.22em] text-slate-500">THE DECISION UNDER ATTACK</p>
                <h2 className="mt-2 max-w-3xl text-2xl font-black tracking-tight text-slate-100 sm:text-3xl">
                  What is this message trying to make you do?
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
                  TRUST//INTERCEPT investigates the claim, challenges its own conclusion, and creates an independent verification path before you act.
                </p>
              </div>
              <div className="decision-target rounded-xl border border-neon-red/30 bg-neon-red/5 px-4 py-3 lg:min-w-[250px]">
                <p className="font-mono text-[9px] font-bold tracking-[0.2em] text-neon-red">ATTACKER'S INTENDED ACTION</p>
                <p className="mt-1 text-base font-black uppercase text-slate-100">{intendedAction}</p>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-800/80 bg-slate-950/35 px-5 py-4 lg:border-l lg:border-t-0 sm:px-6">
            <div className="grid gap-2 sm:grid-cols-4 lg:grid-cols-1">
              {agentRows.map((agent) => (
                <div key={agent.name} className="agent-mini">
                  <span className="agent-index">{agent.mark}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[10px] font-black tracking-[0.16em] text-slate-200">{agent.name}</span>
                      <span className="font-mono text-[8px] tracking-wider text-neon-green">{agent.state}</span>
                    </div>
                    <p className="mt-0.5 truncate text-[10px] text-slate-500">{agent.role}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="mb-4 grid grid-cols-2 gap-2 rounded-xl border border-slate-800/80 bg-space-950/70 p-1" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={cx(
              "rounded-lg px-4 py-2 font-mono text-[11px] font-bold tracking-wider transition",
              tab === item.id
                ? "bg-neon-cyan/15 text-neon-cyan ring-1 ring-neon-cyan/50 shadow-glow-cyan-soft"
                : "text-slate-500 hover:text-slate-300"
            )}
          >
            {item.label}
            {item.id === "audit" && decisions.length > 0 && (
              <span className="ml-2 rounded-full bg-neon-cyan/20 px-1.5 text-[10px] font-bold text-neon-cyan">
                {decisions.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "audit" ? (
        <AuditLog view={view} />
      ) : (
        <>
          {/* Threat severity gauge + alert banner */}
          <section className="glass-panel p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <PanelTitle>VERDICT — SEVERITY GAUGE &amp; CONFIDENCE BAND</PanelTitle>
              <div className="flex items-center gap-2">
                <VoiceExplanation script={buildVoiceScript(verdict)} />
                <button
                  type="button"
                  onClick={() => setMuted((current) => !current)}
                  aria-pressed={muted}
                  aria-label={muted ? "Unmute alert sounds" : "Mute alert sounds"}
                  title={muted ? "Alert sounds muted — click to unmute" : "Alert sounds on — click to mute"}
                  className={cx(
                    "grid h-9 w-9 place-items-center rounded-full border text-sm transition",
                    muted
                      ? "border-slate-700 bg-space-900 text-slate-500 hover:text-slate-300"
                      : "border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan shadow-glow-cyan-soft"
                  )}
                >
                  {muted ? "🔇" : "🔊"}
                </button>
              </div>
            </div>
            {verdict ? (
              <>
                <ThreatGauge
                  score={verdict.score}
                  confidence={verdict.confidence}
                  actionRequired={verdict.action_required}
                />
                {verdict.summary && (
                  <p className="mt-4 text-sm leading-relaxed text-slate-300">{verdict.summary}</p>
                )}
                {verdict.uncertainty_note && (
                  <div className="mt-4 rounded-lg border border-neon-cyan/30 bg-neon-cyan/5 p-3 text-sm text-cyan-100">
                    <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-neon-cyan">
                      UNCERTAINTY:{" "}
                    </span>
                    {verdict.uncertainty_note}
                  </div>
                )}
              </>
            ) : (
              <div className="mt-3 rounded-lg border border-slate-700 bg-space-950/70 p-4 text-sm text-slate-400">
                No verdict has been recorded for this case yet.
                <button
                  type="button"
                  onClick={load}
                  className="ml-2 font-semibold text-neon-cyan hover:underline"
                >
                  Refresh
                </button>
              </div>
            )}

            {/* What TRUST//INTERCEPT did NOT check — always visible (blueprint requirement) */}
            <div className="mt-4 rounded-lg border border-slate-800 bg-space-950/70 p-3">
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                WHAT TRUST//INTERCEPT DID NOT CHECK
              </p>
              <ul className="mt-1.5 list-inside list-disc space-y-1 text-xs text-slate-400">
                {notChecked.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          </section>

          {/* Reasoning tree */}
          <div className="mt-4">
            <ReasoningTree view={view} />
          </div>

              {/* Evidence Arena — adversarial reasoning made inspectable */}
          <section className="mt-4 glass-panel overflow-hidden border-slate-700/80 p-4 sm:p-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <PanelTitle>AGENTIC EVIDENCE ARENA</PanelTitle>
                <h2 className="mt-2 text-xl font-black tracking-tight text-slate-100 sm:text-2xl">
                  Agents must <span className="text-neon-cyan">challenge the evidence</span>, not echo it.
                </h2>
                <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
                  Hunter searches for attack signals. Skeptic actively looks for benign explanations. Verifier identifies
                  the independent evidence that could change the decision. The Arbiter resolves the record without hiding disagreement.
                </p>
              </div>
              <div className="rounded-lg border border-slate-700 bg-space-950/70 px-3 py-2 font-mono text-[9px] tracking-wider text-slate-500">
                {debateResolution?.consensus ? `CONSENSUS · ${String(debateResolution.consensus).replaceAll("_", " ").toUpperCase()}` : "ARENA · OFFLINE-CAPABLE"}
              </div>
            </div>

            <div className="mt-5 grid gap-3 lg:grid-cols-3">
              {[
                {
                  key: "red",
                  number: "01",
                  name: "HUNTER",
                  label: "ATTACK EVIDENCE",
                  data: debateRound?.red,
                  accent: "border-neon-red/30 bg-neon-red/5",
                  text: "text-neon-red",
                },
                {
                  key: "blue",
                  number: "02",
                  name: "SKEPTIC",
                  label: "FALSE-POSITIVE CHALLENGE",
                  data: debateRound?.blue,
                  accent: "border-neon-cyan/30 bg-neon-cyan/5",
                  text: "text-neon-cyan",
                },
                {
                  key: "verifier",
                  number: "03",
                  name: "VERIFIER",
                  label: "WHAT COULD CHANGE THE DECISION?",
                  data: debateRound?.verifier,
                  accent: "border-neon-green/30 bg-neon-green/5",
                  text: "text-neon-green",
                },
              ].map((agent) => (
                <article key={agent.key} className={`rounded-xl border p-4 ${agent.accent}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`grid h-7 w-7 place-items-center rounded-md border border-current/20 font-mono text-[9px] font-black ${agent.text}`}>
                        {agent.number}
                      </span>
                      <div>
                        <p className="font-mono text-[10px] font-black tracking-[0.16em] text-slate-100">{agent.name}</p>
                        <p className="font-mono text-[8px] tracking-wider text-slate-500">{agent.label}</p>
                      </div>
                    </div>
                    {agent.data?.score_vote && (
                      <span className="rounded-full border border-slate-700 bg-space-950/80 px-2 py-1 font-mono text-[9px] font-bold uppercase text-slate-300">
                        VOTE · {agent.data.score_vote}
                      </span>
                    )}
                  </div>

                  {agent.key !== "verifier" ? (
                    <div className="mt-4 space-y-2">
                      {(agent.data?.arguments || []).slice(0, 3).map((argument, index) => (
                        <div key={`${agent.key}-${index}`} className="rounded-lg border border-slate-800 bg-space-950/75 p-2.5">
                          <p className="text-xs font-semibold leading-relaxed text-slate-300">{argument.claim}</p>
                          {argument.evidence_quote && (
                            <p className="mt-1.5 border-l-2 border-slate-700 pl-2 font-mono text-[9px] leading-relaxed text-slate-500">
                              “{argument.evidence_quote}”
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {(agent.data?.tests || []).slice(0, 4).map((test, index) => (
                        <div key={index} className="flex gap-2 rounded-lg border border-slate-800 bg-space-950/75 p-2.5 text-xs leading-relaxed text-slate-300">
                          <span className="font-mono font-bold text-neon-green">0{index + 1}</span>
                          <span>{test}</span>
                        </div>
                      ))}
                      {agent.data?.overturn_condition && (
                        <div className="mt-2 rounded-lg border border-neon-green/20 bg-neon-green/5 p-2.5 text-[10px] leading-relaxed text-neon-green/80">
                          <strong>OVERTURN CONDITION:</strong> {agent.data.overturn_condition}
                        </div>
                      )}
                    </div>
                  )}
                </article>
              ))}
            </div>

            <div className="mt-3">
              <EvidenceChallengeMatrix debate={debateEvidence} />
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1.2fr]">
              <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
                <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">ARBITER RESOLUTION</p>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {[
                    ["HUNTER", debateResolution?.red_vote || "—"],
                    ["SKEPTIC", debateResolution?.blue_vote || "—"],
                    ["CONSENSUS", debateResolution?.consensus?.replaceAll("_", " ") || "—"],
                    ["JUDGE", debateResolution?.judge_used ? "LLM" : "RULES"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/70 p-2.5">
                      <p className="font-mono text-[8px] tracking-wider text-slate-500">{label}</p>
                      <p className="mt-1 text-xs font-bold uppercase text-slate-200">{value}</p>
                    </div>
                  ))}
                </div>
                {debateResolution?.policy && (
                  <p className="mt-3 text-[10px] leading-relaxed text-slate-500">Policy: {debateResolution.policy}</p>
                )}
              </div>

              <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
                <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">INVESTIGATION TIMELINE</p>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {evidenceTimeline.slice(0, 12).map((item) => (
                    <div key={`${item.index}-${item.tool}`} className="group relative flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1.5">
                      <span className="grid h-4 w-4 place-items-center rounded bg-neon-cyan/10 font-mono text-[8px] font-bold text-neon-cyan">{item.index}</span>
                      <span className="font-mono text-[9px] text-slate-400">{item.tool}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-[9px] text-slate-600">Evidence is captured in execution order. Failed external checks remain visible instead of disappearing.</p>
              </div>
            </div>
          </section>

      {/* Decision Defence Engine — the product's differentiating layer */}
          {defenceEvidence && (
            <section className="mt-4 glass-panel overflow-hidden border-neon-cyan/30 p-4 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <PanelTitle>DECISION DEFENCE ENGINE</PanelTitle>
                  <h2 className="mt-2 text-xl font-black tracking-tight text-slate-100 sm:text-2xl">
                    Break the <span className="neon-cyan-text">attack chain</span> before it reaches you.
                  </h2>
                  <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-500">
                    The system does not stop at “scam / not scam”. It identifies the decision the sender is trying to force,
                    then gives you an independent way to verify the claim.
                  </p>
                </div>
                <div className="min-w-[150px] rounded-xl border border-neon-cyan/30 bg-neon-cyan/5 px-4 py-3 text-right">
                  <p className="font-mono text-[9px] font-bold tracking-[0.2em] text-slate-500">DECISION SAFETY</p>
                  <p className="mt-1 font-mono text-3xl font-black text-neon-cyan">
                    {defenceEvidence.decision_safety_score ?? "—"}
                  </p>
                  <p className="font-mono text-[9px] uppercase tracking-wider text-slate-500">/ 100</p>
                </div>
              </div>

              <div className="mt-5 grid gap-3 lg:grid-cols-[1.35fr_.9fr]">
                <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
                  <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">ATTACKER INTENDED ACTION</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(defenceEvidence.intended_actions || []).map((action) => (
                      <span key={action} className="rounded-full border border-neon-red/40 bg-neon-red/10 px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-neon-red">
                        {action.replaceAll("_", " ")}
                      </span>
                    ))}
                  </div>

                  <div className="mt-4">
                    <ManipulationGraph
                      attackChain={defenceEvidence.attack_chain}
                      cues={verdict?.cues || []}
                      intendedActions={defenceEvidence.intended_actions || []}
                      recommendation={defenceEvidence.recommendation || "VERIFY"}
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="rounded-xl border border-gold-neon/30 bg-gold-neon/5 p-4">
                    <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-gold-neon">RECOMMENDATION</p>
                    <p className="mt-2 text-2xl font-black text-slate-100">{defenceEvidence.recommendation || "VERIFY"}</p>
                    <p className="mt-1 text-xs text-slate-500">This is guidance, not an automatic action.</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
                    <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">SAFE VERIFICATION</p>
                    <ol className="mt-2 space-y-2 text-xs leading-relaxed text-slate-300">
                      {(defenceEvidence.safe_verification || []).map((step, index) => (
                        <li key={step} className="flex gap-2">
                          <span className="font-mono font-bold text-neon-cyan">0{index + 1}</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </div>

              <CounterfactualVerification verification={verificationEvidence} />

              <div className="mt-3 rounded-xl border border-neon-green/25 bg-neon-green/5 p-4">
                <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-neon-green">COUNTERFACTUAL CHECK</p>
                <p className="mt-1 text-sm font-semibold text-slate-200">{defenceEvidence.counterfactual?.question}</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {(defenceEvidence.counterfactual?.conditions || []).map((condition) => (
                    <div key={condition} className="rounded-lg border border-slate-800 bg-space-950/70 p-2.5 text-xs text-slate-400">
                      {condition}
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-neon-green/80">
                  <strong>Try to disprove us:</strong> {defenceEvidence.counterfactual?.how_to_try_to_disprove_us}
                </p>
              </div>
            </section>
          )}

          {/* Warning banner (after Block/Warn approval) */}
          {warningShown && (
            <div className="mt-4 glass-panel animate-pulse-glow border-gold-neon/60 p-4">
              <p className="font-mono text-sm font-black tracking-wider text-gold-neon">
                ⚠ WARNING SHOWN — APPROVED ACTION
              </p>
              <p className="mt-1 text-sm text-amber-100">{warningShown}</p>
              <p className="mt-2 text-xs text-amber-300/70">
                Note: TRUST//INTERCEPT never auto-blocks real contacts or numbers — this is guidance, not
                device-level enforcement.
              </p>
            </div>
          )}

          {/* Safe confirmation (after Looks Safe) */}
          {safeConfirmed && (
            <div className="mt-4 glass-panel border-neon-green/60 p-4 text-sm text-emerald-100">
              <p className="font-mono text-sm font-black tracking-wider text-neon-green">
                ✓ CASE MARKED SAFE BY HUMAN APPROVAL
              </p>
              <p className="mt-1 text-xs text-emerald-200/80">
                Nothing was blocked, sent, or filed. Want to reinforce the lesson anyway?{" "}
                <Link to={`/case/${caseId}/coach`} className="font-semibold text-neon-green underline">
                  Take the awareness quiz
                </Link>
                .
              </p>
            </div>
          )}

          {/* Highlighted message */}
          {caseInfo.redacted_text && (
            <section className="mt-4 glass-panel p-4 sm:p-6">
              <PanelTitle>MODULE 1 — EXPLAINABLE PHISHING CUES (PII REDACTED)</PanelTitle>
              <div className="mt-3">
                <CueHighlighter text={caseInfo.redacted_text} cues={cues} />
              </div>
            </section>
          )}

          {/* Safe destination inspection — never encourage opening the suspicious destination. */}
          {chains.length > 0 && (
            <section className="mt-4 glass-panel border-neon-cyan/30 p-4 sm:p-6">
              <PanelTitle>MODULE 2 — DESTINATION INSPECTION BEFORE VISIT</PanelTitle>
              <div className="mt-3 rounded-xl border border-neon-cyan/40 bg-neon-cyan/5 p-4">
                <div className="flex items-start gap-3">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 font-mono text-sm font-black text-neon-cyan">
                    ⛨
                  </div>
                  <div>
                    <p className="font-mono text-xs font-black tracking-[0.16em] text-neon-cyan">YOU HAVE NOT OPENED THE SITE</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">
                      TRUST//INTERCEPT inspected the URL, redirect chain, domain intelligence and available reputation signals first.
                      Do not use contact details or links supplied by the suspicious message to verify the claim.
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-3">
                <RedirectChain chains={chains} domains={domains} />
              </div>
            </section>
          )}

          {/* Evidence Passport — provenance snapshot before the human decision. */}
          <div className="mt-4">
            <EvidencePassport caseInfo={caseInfo} verdict={verdict} evidence={view?.evidence || []} />
          </div>

          <CaseReplay provenance={view?.provenance} />

          {/* The structural gate: explicit action buttons */}
          <section className="mt-4 glass-panel border-blue-400/30 p-4 sm:p-6">
            <PanelTitle>YOUR DECISION — NOTHING HAPPENS UNTIL YOU CHOOSE (SECTION 05 GATE)</PanelTitle>

            {/* Psychological Shield — 10-second cooling-off barrier */}
            {coolingOff > 0 && (
              <div
                role="alertdialog"
                aria-label="Cooling-off barrier"
                className="mt-3 rounded-xl border border-gold-neon/60 bg-gold-neon/10 p-4 shadow-glow-gold"
              >
                <p className="font-mono text-xs font-black tracking-[0.18em] text-gold-neon">
                  ⏸ COOLING-OFF BARRIER — {coolingOff}s
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-amber-100">
                  This message scored <strong>{Math.round((radarEvidence?.overall || 0) * 100)}%</strong> on the
                  manipulation radar. Scammers manufacture urgency precisely so you act before thinking.
                  Take ten seconds. The scam can wait for you — you don't have to hurry for it.
                </p>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-space-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-neon-gold to-neon-red transition-all duration-1000 ease-linear"
                    style={{ width: `${coolingOff * 10}%` }}
                  />
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    disabled={coolingOff > 0}
                    onClick={() => handleDecision(coolingAction, { skipCooling: true })}
                    className="rounded-lg border border-gold-neon/60 bg-gold-neon/15 px-4 py-2 text-sm font-bold text-gold-neon transition disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {coolingOff > 0 ? `WAIT ${coolingOff}s…` : "CONTINUE — I'VE TAKEN MY TIME"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCoolingOff(0);
                      setCoolingAction(null);
                    }}
                    className="rounded-lg border border-slate-600 bg-space-900 px-4 py-2 text-sm font-bold text-slate-300 transition hover:text-white"
                  >
                    CANCEL — GOOD, THINK IT OVER
                  </button>
                </div>
              </div>
            )}

            {/* Trusted Caregiver Safety Circle — escalation for high-pressure cases */}
            {caregiverEligible && (
              <div className="mt-3 rounded-xl border border-neon-green/30 bg-space-950/60 p-3">
                <p className="font-mono text-[11px] font-bold tracking-[0.16em] text-neon-green">
                  🛡 TRUSTED CAREGIVER ESCALATION — SAFETY CIRCLE
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  High pressure detected ({Math.round((radarEvidence?.overall || 0) * 100)}% manipulation). Send a
                  pre-formatted, fully redacted alert to someone you trust — one tap, nothing sent automatically.
                </p>
                <div className="mt-2 rounded-lg border border-slate-800 bg-slate-900/80 p-2.5">
                  <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-slate-400">
                    {caregiverMessage}
                  </pre>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {circleLinks.map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-lg border border-neon-green/50 bg-neon-green/10 px-3 py-1.5 font-mono text-[11px] font-black tracking-wider text-neon-green transition hover:bg-neon-green/20"
                    >
                      SEND VIA {link.label}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Honeypot Sandbox Recon — counter-intel for high-risk cases */}
            {verdict?.score === "high" && (
              <div className="mt-3 rounded-xl border border-neon-cyan/30 bg-space-950/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-mono text-[11px] font-bold tracking-[0.16em] text-neon-cyan">
                      🛡 HONEYPOT SANDBOX RECON — COUNTER-INTEL
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Isolated one-shot probe: extracts the scammer's C2 IP, hosting provider and tech stack for
                      police reporting. Never opens the site in your browser; sends nothing but the probe request.
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={reconBusy}
                    onClick={handleRecon}
                    className="rounded-lg border border-neon-cyan/60 bg-neon-cyan/15 px-4 py-2 font-mono text-xs font-black tracking-wider text-neon-cyan shadow-glow-cyan-soft transition hover:bg-neon-cyan/25 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {reconBusy ? "◌ PROBING SANDBOX…" : "RUN SAFE SANDBOX RECON"}
                  </button>
                </div>
                {recon && (
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                    {[
                      { label: "C2 / ORIGIN IP", value: recon.findings?.ip || "—" },
                      { label: "HOSTING PROVIDER", value: recon.findings?.hosting_provider || "—" },
                      { label: "TECH STACK", value: recon.findings?.tech_stack || "—" },
                    ].map((cell) => (
                      <div key={cell.label} className="rounded-lg border border-slate-800 bg-slate-900/80 p-2">
                        <p className="font-mono text-[9px] font-bold tracking-[0.18em] text-slate-500">{cell.label}</p>
                        <p className="mt-0.5 break-all font-mono text-xs font-bold text-neon-cyan">{cell.value}</p>
                      </div>
                    ))}
                    {recon.status !== "completed" && (
                      <p className="col-span-full font-mono text-[10px] text-gold-neon">{recon.detail}</p>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {DECISION_BUTTONS.map((button) => (
                <button
                  key={button.action}
                  type="button"
                  disabled={pendingAction !== null}
                  onClick={() => handleDecision(button.action)}
                  title={button.hint}
                  className={cx(
                    "rounded-xl px-4 py-3 text-sm font-bold tracking-wide transition disabled:cursor-not-allowed disabled:opacity-50",
                    button.className
                  )}
                >
                  {pendingAction === button.action ? "WORKING…" : button.label}
                </button>
              ))}
            </div>

            {showCorrection && (
              <div className="mt-4 rounded-lg border border-slate-700 bg-space-950/70 p-3">
                <label htmlFor="correction" className="block text-sm text-slate-300">
                  What did TRUST//INTERCEPT get wrong? Your correction will be redacted, noted and logged — the
                  original verdict is preserved.
                </label>
                <textarea
                  id="correction"
                  rows={3}
                  value={correction}
                  onChange={(event) => setCorrection(event.target.value)}
                  placeholder="e.g. This really is my courier — the link matches their official site."
                  className="mt-2 w-full resize-y rounded-lg border border-slate-700 bg-space-900 p-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-neon-cyan/60 focus:outline-none focus:ring-2 focus:ring-neon-cyan/25"
                />
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={pendingAction !== null || !correction.trim()}
                    onClick={() => handleDecision("disagree_recheck")}
                    className="gate-btn gate-disagree rounded-lg px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {pendingAction === "disagree_recheck" ? "RE-CHECKING…" : "RE-CHECK WITH MY CORRECTION"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCorrection(false);
                      setCorrection("");
                    }}
                    className="px-4 py-2 font-mono text-xs tracking-wider text-slate-500 hover:text-slate-300"
                  >
                    CANCEL
                  </button>
                </div>
              </div>
            )}

            {error && view && (
              <div role="alert" className="mt-4 rounded-lg border border-neon-red/40 bg-neon-red/10 p-3 text-sm text-red-200">
                {error}
              </div>
            )}
          </section>

          {/* Explainability trace */}
          {view?.evidence?.length > 0 && (
            <section className="mt-4 glass-panel p-4 sm:p-6">
              <button
                type="button"
                onClick={() => setShowTrace((current) => !current)}
                className="flex w-full items-center justify-between text-left"
              >
                <PanelTitle>
                  REASONING TRACE — TOOLS, PROMPTS &amp; LLM RESPONSE ({view.evidence.length} ENTRIES)
                </PanelTitle>
                <span className="text-neon-cyan">{showTrace ? "▲" : "▼"}</span>
              </button>
              {showTrace && (
                <div className="mt-3 space-y-2">
                  {view.evidence.map((entry, index) => (
                    <details key={index} className="rounded-lg border border-slate-800 bg-space-950/70 p-3">
                      <summary className="cursor-pointer text-sm font-medium text-slate-300">
                        <span className="rounded bg-neon-cyan/15 px-1.5 py-0.5 font-mono text-xs text-neon-cyan">
                          {entry.tool}
                        </span>
                        <span className="ml-2 text-xs text-slate-500">{formatDateTime(entry.collected_at)}</span>
                      </summary>
                      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-space-950 p-3 font-mono text-[11px] leading-relaxed text-neon-cyan/90">
                        {JSON.stringify(entry.raw_output, null, 2)}
                      </pre>
                    </details>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Decision history (compact, on verdict tab) */}
          {decisions.length > 0 && (
            <section className="mt-4 mb-8 glass-panel p-4 sm:p-6">
              <PanelTitle>DECISION LOG — EVERY ACTION IS APPROVED BY A HUMAN AND SNAPSHOTTED</PanelTitle>
              <ul className="mt-3 space-y-2">
                {decisions.map((decision, index) => (
                  <li key={decision.id || index} className="rounded-lg border border-slate-800 bg-space-950/70 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-neon-cyan/15 px-2 py-0.5 font-mono text-xs font-bold text-neon-cyan">
                        {ACTION_LABELS[decision.human_action] || decision.human_action}
                      </span>
                      <span className="text-xs text-slate-500">
                        {formatDateTime(decision.decided_at)} · by {decision.decided_by}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-300">{decision.action_taken}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-500">
                Full audit view (risk deltas + verification hashes) is on the{" "}
                <button type="button" onClick={() => setTab("audit")} className="font-semibold text-neon-cyan hover:underline">
                  Audit Log
                </button>{" "}
                tab.
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
