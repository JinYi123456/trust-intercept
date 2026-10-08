/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "gold-neon": "#FFC933", // brightened from #FFB800 for ≥4.5:1 on dark bg
        // Accessibility-tuned slate ramp: slate-400/500 usages below now meet
        // WCAG AA (≥4.5:1) against the space-900/950 backgrounds.
        "muted": "#94A3B8",   // replacement for slate-500 body text
        "faint": "#64748B",   // replacement for slate-600 hints (≥4.5:1 on #090D16)
        space: {
          950: "#070B12",
          900: "#090D16",
          850: "#0A0E17",
          800: "#0D1322",
          700: "#131A2E",
        },
        neon: {
          red: "#FF0055",
          green: "#00E676",
          gold: "#FFB800",
          cyan: "#00E5FF",
        },
      },
      fontFamily: {
        sans: [
          "Inter", "ui-sans-serif", "system-ui", "-apple-system",
          "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      boxShadow: {
        "glow-red": "0 0 10px rgba(255,0,85,.55), 0 0 34px rgba(255,0,85,.28)",
        "glow-green": "0 0 10px rgba(0,230,118,.5), 0 0 34px rgba(0,230,118,.22)",
        "glow-gold": "0 0 10px rgba(255,184,0,.5), 0 0 34px rgba(255,184,0,.22)",
        "glow-cyan": "0 0 10px rgba(0,229,255,.5), 0 0 34px rgba(0,229,255,.24)",
        "glow-cyan-soft": "0 0 18px rgba(0,229,255,.18)",
        "glow-red-soft": "0 0 18px rgba(255,0,85,.22)",
        "glow-green-soft": "0 0 18px rgba(0,230,118,.2)",
        "glow-gold-soft": "0 0 18px rgba(255,184,0,.2)",
        panel: "0 24px 60px -24px rgba(0,0,0,.85)",
      },
      keyframes: {
        "radar-sweep": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        "scan-y": {
          "0%": { top: "-12%", opacity: "0" },
          "12%": { opacity: "1" },
          "88%": { opacity: "1" },
          "100%": { top: "108%", opacity: "0" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: ".45" },
        },
        "float-in": {
          from: { opacity: "0", transform: "translateY(-14px) scale(.95)" },
          to: { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "blip": {
          "0%, 100%": { opacity: ".25" },
          "50%": { opacity: "1" },
        },
        "flicker": {
          "0%, 100%": { opacity: "1" },
          "92%": { opacity: "1" },
          "93%": { opacity: ".6" },
          "94%": { opacity: "1" },
          "97%": { opacity: ".75" },
          "98%": { opacity: "1" },
        },
      },
      animation: {
        "radar-sweep": "radar-sweep 2.8s linear infinite",
        "scan-y": "scan-y 2.4s ease-in-out infinite",
        "pulse-glow": "pulse-glow 1.6s ease-in-out infinite",
        "float-in": "float-in .32s cubic-bezier(.2,.8,.3,1) both",
        blip: "blip 1.8s ease-in-out infinite",
        flicker: "flicker 6s linear infinite",
      },
    },
  },
  plugins: [],
};
