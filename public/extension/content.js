/**
 * TrustIntercept Overlay — content script (Manifest V3).
 *
 * Mirrors the in-app "Analyze with TrustIntercept" selection badge on ANY web page:
 * when the user selects suspicious text, a floating cyber badge appears
 * near the selection; clicking it opens the TrustIntercept hub and hands the text
 * over via sessionStorage (the hub's SelectionBridge picks it up, prefills
 * the intake, and starts the live analysis).
 */

const BADGE_ID = "trust-intercept-analyze-badge";

let badge = null;

function removeBadge() {
  if (badge) {
    badge.remove();
    badge = null;
  }
}

function selectedText() {
  const selection = window.getSelection();
  return selection ? selection.toString().trim() : "";
}

function showBadge() {
  const text = selectedText();
  if (text.length < 3) {
    removeBadge();
    return;
  }
  removeBadge();

  const range = window.getSelection().getRangeAt(0);
  const rect = range.getBoundingClientRect();

  badge = document.createElement("div");
  badge.id = BADGE_ID;
  badge.textContent = "\u{1F50D} Analyze with TrustIntercept";
  badge.style.position = "fixed";
  badge.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - 200))}px`;
  badge.style.top = `${Math.max(8, rect.top - 38)}px`;
  badge.style.zIndex = "2147483647";

  badge.addEventListener("mousedown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    sessionStorage.setItem("trust-intercept_selected_text", text);
    window.open("http://127.0.0.1:5173/?trust-intercept_prefill=1", "_blank");
    removeBadge();
  });

  document.body.appendChild(badge);
}

document.addEventListener("selectionchange", () => {
  clearTimeout(window.__trust-interceptBadgeTimer);
  window.__trust-interceptBadgeTimer = setTimeout(() => {
    if (selectedText()) showBadge();
    else removeBadge();
  }, 220);
});

document.addEventListener("click", (event) => {
  if (badge && !badge.contains(event.target)) removeBadge();
});
