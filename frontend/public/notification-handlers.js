/*
 * TRUST//INTERCEPT — native OS notification click handling.
 *
 * Injected into the generated PWA service worker via vite.config.js
 * (workbox.importScripts). The SocialThreatSimulator shows system-level
 * notifications through registration.showNotification(); this handler makes
 * clicking the OS banner focus the TRUST//INTERCEPT window (even if minimized) and
 * forwards the simulated threat id so the app loads it into the live pipeline.
 */

self.addEventListener("notificationclick", (event) => {
  const data = (event.notification && event.notification.data) || {};
  event.notification.close();

  event.waitUntil(
    (async () => {
      // Focus an already-open TRUST//INTERCEPT window when possible.
      const clientList = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });

      for (const client of clientList) {
        if (client.url && client.url.startsWith(self.registration.scope)) {
          await client.focus();
          client.postMessage({
            type: "trust-intercept-simulated-threat",
            threatId: data.threatId || null,
            url: data.url || "/",
          });
          return;
        }
      }

      // Nothing open — launch TRUST//INTERCEPT; the app replays the threat on load.
      await self.clients.openWindow((data && data.url) || "/");
    })()
  );
});
