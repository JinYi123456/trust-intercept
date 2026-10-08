import { Component } from "react";

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // Keep crash details out of the UI and avoid transmitting suspicious case data.
    if (import.meta.env.DEV) console.error("TRUST//INTERCEPT UI error", error);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-xl items-center px-4 py-12">
        <section className="glass-panel w-full p-6 text-center" role="alert">
          <p className="label-cyber text-neon-red">INTERFACE RECOVERY</p>
          <h1 className="mt-2 text-2xl font-black text-slate-100">This view could not be rendered.</h1>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Your case data has not been sent anywhere by this error screen. Reload the interface and retry the investigation if needed.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="btn-cyber mt-5 border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/20"
          >
            RELOAD INTERFACE
          </button>
        </section>
      </main>
    );
  }
}
