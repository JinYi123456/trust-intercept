import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// The frontend talks to the FastAPI backend directly via VITE_API_BASE_URL
// (default http://127.0.0.1:8000) — see src/api/client.js. No proxy needed.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // "generateSW" keeps things simple and reliable for the hackathon demo.
      strategies: "generateSW",
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "icons/*.png"],
      manifest: {
        id: "trust-intercept-scam-defence",
        name: "TRUST//INTERCEPT — Scam Defence Agent",
        short_name: "TRUST//INTERCEPT",
        description:
          "Explainable, multi-modal scam defence. TRUST//INTERCEPT investigates and explains; the person decides.",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait-primary",
        background_color: "#f8fafc",
        theme_color: "#0f172a",
        lang: "en",
        dir: "ltr",
        categories: ["security", "productivity", "utilities"],
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "/icons/icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
          { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Native OS notification click handling (SocialThreatSimulator):
        // focus TRUST//INTERCEPT + forward the simulated threat into the live pipeline.
        importScripts: ["/notification-handlers.js"],
        // Keep the installed app usable offline: the shell + assets are
        // precached; API calls are never cached (verdicts must be fresh) and
        // fall back to an offline notice page when the backend is unreachable.
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        navigateFallback: "/offline.html",
        navigateFallbackDenylist: [/^\/case\//],
        runtimeCaching: [
          {
            urlPattern: ({ url }) =>
              url.origin === self?.location?.origin && url.pathname.startsWith("/assets/"),
            handler: "CacheFirst",
            options: { cacheName: "trust-intercept-assets", expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 * 30 } },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 5173,
    host: true,
  },
  preview: {
    port: 5173,
    host: true,
  },
});
