/**
 * TRUST//INTERCEPT API client.
 *
 * Contract (matches the blueprint's routers):
 *  - POST /case                      -> CaseView {case, evidence, verdict, decisions, report, quiz}
 *  - GET  /case/{id}                 -> CaseView
 *  - POST /case/{id}/decision        -> CaseView (the ONLY endpoint that writes action_taken)
 *  - POST /case/{id}/coach           -> Quiz
 *  - GET  /case/{id}/report?format=markdown -> downloadable report file
 */
// Default matches the FastAPI backend exactly: http://127.0.0.1:8000
// (the backend's CORS allow-list covers both 127.0.0.1 and localhost on port 5173).
// Override with VITE_API_BASE_URL for LAN/phone testing (e.g. http://192.168.x.x:8000).
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    throw new Error(
      `Cannot reach the TRUST//INTERCEPT API at ${BASE_URL}. Make sure the backend is running ` +
        `(uvicorn backend.main:app --reload) and that VITE_API_BASE_URL points at it.`
    );
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        detail = data.detail
          .map((item) => `${(item.loc || []).join(".")}: ${item.msg}`)
          .join("; ");
      }
    } catch (parseError) {
      // Keep the default status-text detail.
    }
    throw new Error(detail);
  }

  return response.json();
}

export const api = {
  baseUrl: BASE_URL,

  health: () => request("/health"),

  /** Live command-center telemetry for the metrics dashboard (GET /metrics). */
  getMetrics: () => request("/metrics"),

  submitCase: (payload) => request("/case", { method: "POST", body: payload }),

  getCase: (caseId) => request(`/case/${encodeURIComponent(caseId)}`),

  /** The structural human-approval gate. payload: {human_action, correction?, decided_by?} */
  postDecision: (caseId, payload) =>
    request(`/case/${encodeURIComponent(caseId)}/decision`, { method: "POST", body: payload }),

  /** Module 4 — launch the awareness quiz for the detected scam pattern. */
  submitCoach: (caseId, answers) => request(`/case/${caseId}/coach/submit`, { method: "POST", body: { answers } }),
  getCoachMastery: (caseId) => request(`/case/${caseId}/coach/mastery`),
  launchCoach: (caseId) => request(`/case/${encodeURIComponent(caseId)}/coach`, { method: "POST" }),

  /** Federated Scam Intelligence Network — anonymous threat-indicator hashes. */
  communityStats: () => request("/community/stats"),

  postCommunityHash: (payload) =>
    request("/community/report-hash", { method: "POST", body: payload }),

  /** Honeypot Sandbox Recon — isolated probe of a high-risk case's URL (gated). */
  runSandboxRecon: (caseId) =>
    request(`/case/${encodeURIComponent(caseId)}/recon`, { method: "POST" }),

  /** Module 3 — the backend streams the redacted report as a markdown download. */
  reportUrl: (caseId) => `${BASE_URL}/case/${encodeURIComponent(caseId)}/report?format=markdown`,
};

export default api;
