import { useLang } from "../lib/i18n.jsx";
import { cx } from "../lib/ui";

/**
 * Shared async-state primitives so every API call has a consistent
 * loading / error / offline treatment, plus the single "Details"
 * disclosure used to collapse secondary panels.
 */

/** Accessible spinner + label. Wrap in a min-height to avoid layout jumps. */
export function Loading({ label, className }) {
  const { t } = useLang();
  return (
    <div
      role="status"
      aria-live="polite"
      className={cx("flex flex-col items-center justify-center gap-3 py-16", className)}
    >
      <span
        aria-hidden="true"
        className="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-neon-cyan"
      />
      <span className="font-mono text-xs tracking-[0.2em] text-slate-400">{label || t("loadingGeneric")}</span>
    </div>
  );
}

/** Full-screen error with retry — used when a page's primary load fails. */
export function ErrorState({ message, onRetry, backLink }) {
  const { t } = useLang();
  return (
    <div className="mx-auto max-w-3xl">
      <div
        role="alert"
        className="glass-panel border-neon-red/50 p-5"
      >
        <p className="flex items-center gap-2 font-bold text-red-100">
          <span aria-hidden="true">⚠️</span> Something went wrong
        </p>
        <p className="mt-2 text-sm leading-relaxed text-red-200">{message}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-lg border border-neon-cyan/60 bg-neon-cyan/15 px-4 py-2 text-sm font-bold text-neon-cyan transition hover:bg-neon-cyan/25 focus-visible:ring-2 focus-visible:ring-neon-cyan"
            >
              ⟳ {t("retry")}
            </button>
          )}
          {backLink}
        </div>
      </div>
    </div>
  );
}

/** Inline error shown near an action that failed (keeps page content visible). */
export function InlineError({ message }) {
  return (
    <div role="alert" className="mt-3 rounded-lg border border-neon-red/50 bg-neon-red/10 p-3 text-sm text-red-200">
      <span className="font-bold" aria-hidden="true">⚠️ </span>
      {message}
    </div>
  );
}

/** Global offline banner — rendered by App when navigator.onLine is false. */
export function OfflineBanner() {
  const { t } = useLang();
  return (
    <div
      role="alert"
      className="border-b border-gold-neon/50 bg-gold-neon/15 px-4 py-2 text-center text-sm font-semibold text-amber-100"
    >
      <span aria-hidden="true">📶 </span>
      {t("offlineBanner")}
    </div>
  );
}

/**
 * Collapsible secondary panel. The chevron and +/- glyph give a non-colour
 * open/closed signal, and aria-expanded keeps screen readers in sync.
 */
export function Details({ title, subtitle, children, defaultOpen = false }) {
  const { t } = useLang();
  return (
    <section className="glass-panel p-4 sm:p-5">
      <details open={defaultOpen} className="group">
        <summary
          className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
        >
          <span>
            <span className="block text-sm font-bold text-slate-200">{title}</span>
            {subtitle && <span className="mt-0.5 block text-xs text-slate-400">{subtitle}</span>}
          </span>
          <span className="flex shrink-0 items-center gap-2 font-mono text-[11px] font-bold text-neon-cyan">
            <span className="group-open:hidden">{t("detailsShow")} +</span>
            <span className="hidden group-open:inline">{t("detailsHide")} −</span>
            <span aria-hidden="true" className="transition group-open:rotate-180">▼</span>
          </span>
        </summary>        <div className="mt-4">{children}</div>
      </details>
    </section>
  );
}
