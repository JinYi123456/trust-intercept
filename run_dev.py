"""TrustIntercept dev launcher with automatic port fallback.

Checks port 8001 (8000 is RESERVED for the separate logistics snapshot API
project on this machine — never bind it); if occupied, walks 8002..8004 and
reconfigures the frontend to match (writes VITE_API_BASE_URL into
frontend/.env), then starts BOTH servers and health-checks them.

Usage:
    python run_dev.py                 # backend 8001->fallback, frontend 5173
    python run_dev.py --no-frontend   # backend only
    python run_dev.py --port 8002     # force a specific backend port

Standalone (manual) commands, if you prefer two terminals:
    Terminal 1:  .venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port <PORT>
    Terminal 2:  cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
                 (frontend/.env already points VITE_API_BASE_URL at <PORT>)
"""
from __future__ import annotations

import argparse
import atexit
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def pick_backend_port(preferred: int, force: int | None) -> int:
    if force is not None:
        if not port_free(force):
            raise SystemExit(f"ERROR: forced port {force} is occupied.")
        return force
    for candidate in range(preferred, preferred + 4):  # 8001 -> 8002 -> 8003 -> 8004
        if port_free(candidate):
            if candidate != preferred:
                print(f"[port] {preferred} is OCCUPIED -> auto-fallback to {candidate}")
            else:
                print(f"[port] {preferred} is free")
            return candidate
    raise SystemExit("ERROR: no free port in range 8001-8004.")


def sync_frontend_env(port: int) -> None:
    """Point VITE_API_BASE_URL at the ACTIVE backend port (idempotent)."""
    env_path = ROOT / "frontend" / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = [
            line
            for line in env_path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("VITE_API_BASE_URL") and line.strip()
        ]
    lines.insert(0, f"VITE_API_BASE_URL=http://127.0.0.1:{port}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[env ] wrote {env_path.relative_to(ROOT)} -> VITE_API_BASE_URL=http://127.0.0.1:{port}")


def backend_python() -> str:
    """Prefer the project venv so the backend always has its dependencies,
    even if this script itself was launched with the global interpreter."""
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",  # Windows
        ROOT / ".venv" / "bin" / "python",           # macOS / Linux
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def wait_for(url: str, timeout: float, label: str) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    print(f"[ok  ] {label} answering at {url}")
                    return
        except Exception:
            time.sleep(1.0)
    raise SystemExit(f"ERROR: {label} did not come up at {url} within {timeout:.0f}s.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start TrustIntercept backend + frontend with port auto-fallback.")
    parser.add_argument("--port", type=int, default=None, help="Force a specific backend port")
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--no-frontend", action="store_true", help="Start the backend only")
    args = parser.parse_args()

    # NOTE: 8000 is reserved for the logistics snapshot API project on this
    # machine — TrustIntercept must never bind it, even when it happens to be free.
    port = pick_backend_port(8001, args.port)
    sync_frontend_env(port)

    # Frontend port: also auto-fallback so Vite never surprises us mid-launch.
    frontend_port = args.frontend_port
    if not args.no_frontend:
        for candidate in range(args.frontend_port, args.frontend_port + 4):
            if port_free(candidate):
                frontend_port = candidate
                break
        else:
            raise SystemExit("ERROR: no free frontend port in range.")

    # --- Backend ---------------------------------------------------------
    backend = subprocess.Popen(
        [backend_python(), "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
    )
    print(f"[boot] backend  -> http://127.0.0.1:{port}  (pid {backend.pid})")

    frontend = None
    try:
        wait_for(f"http://127.0.0.1:{port}/health", timeout=40, label="backend")
    except SystemExit:
        backend.terminate()
        raise

    # --- Frontend --------------------------------------------------------
    if not args.no_frontend:
        npm_cmd = "npm run dev"
        frontend = subprocess.Popen(
            npm_cmd + f" -- --host 127.0.0.1 --port {frontend_port}",
            cwd=ROOT / "frontend",
            shell=(os.name == "nt"),
        )
        print(f"[boot] frontend -> http://127.0.0.1:{frontend_port}  (pid {frontend.pid})")
        try:
            wait_for(f"http://127.0.0.1:{frontend_port}/", timeout=60, label="frontend")
        except SystemExit:
            for proc in (frontend, backend):
                if proc and proc.poll() is None:
                    proc.terminate()
            raise

    print()
    print("=" * 64)
    print(f"  TrustIntercept is running:")
    print(f"    API      : http://127.0.0.1:{port}      (docs: /docs)")
    print(f"    Frontend : http://127.0.0.1:{frontend_port}")
    print("  Press Ctrl+C to stop both servers.")
    print("=" * 64)

    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (frontend, backend):
            if proc and proc.poll() is None:
                proc.terminate()
        print("[exit] servers stopped.")


if __name__ == "__main__":
    atexit.register(lambda: None)
    main()
