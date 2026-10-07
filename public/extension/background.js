/**
 * TrustIntercept Overlay — service worker (Manifest V3).
 *
 * Right-click context menu: "Analyze selected text with TrustIntercept". Hands the
 * selection to the hub the same way the floating badge does (sessionStorage
 * on the hub origin + a query flag), then opens the hub.
 */

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "trust-intercept-analyze-selection",
    title: "Analyze selected text with TrustIntercept",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "trust-intercept-analyze-selection") return;
  const text = String(info.selectionText || "").slice(0, 8000);
  // The hub reads this key from its own sessionStorage on load.
  chrome.tabs.create({ url: "http://127.0.0.1:5173/?trust-intercept_prefill=1" }, (tab) => {
    // sessionStorage lives per-origin in the page, so inject after load.
    if (!tab.id) return;
    chrome.scripting?.executeScript
      ? chrome.tabs.onUpdated.addListener(function listener(tabId, changeInfo) {
          if (tabId === tab.id && changeInfo.status === "complete") {
            chrome.tabs.onUpdated.removeListener(listener);
            chrome.scripting
              .executeScript({
                target: { tabId: tab.id },
                func: (value) => sessionStorage.setItem("trust-intercept_selected_text", value),
                args: [text],
              })
              .catch(() => {});
          }
        })
      : null;
  });
});
