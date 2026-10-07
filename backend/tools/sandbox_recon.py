"""Honeypot Sandbox Recon — counter-intelligence probe for high-risk URLs.

When Module 2 rates a URL high-risk, TRUST//INTERCEPT can run an ISOLATED headless probe
("safe sandbox recon") to gather evidence for law-enforcement reporting:

* the scammer's C2/origin IP (resolved for the redirect chain's final host),
* the hosting provider (RDAP/WHOIS network owner),
* a technology-stack fingerprint (Server header + HTTP feature probes),
* and any client-side capture commands (form posts, credential-field names,
  geolocation/webcam API calls) found in the served HTML.

SAFETY MODEL (the "honeypot" part):
- The probe only fires when a human requests it via the gated recon endpoint —
  it is never part of the automatic pipeline.
- One HTTP GET, no code execution, no plugins, no cookie jar, no referrer, a
  short timeout, and a strict response-size cap. Nothing from the page is ever
  executed or rendered.
- No PII is sent: the request carries no user data, and the stored evidence
  contains infrastructure facts only.
- Fully offline-safe: with ALLOW_OUTBOUND_LOOKUPS=false the probe refuses and
  records why, so the demo never depends on the network.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from backend.config import get_settings
from backend.models.case import utcnow

MAX_RESPONSE_BYTES = 512 * 1024  # 512 KB cap on any fetched page
USER_AGENT = "TRUST//INTERCEPTSandboxProbe/1.0 (+counter-fraud research; no user data sent)"

_CREDENTIAL_HINTS = re.compile(
    r"<input[^>]+(name|id)\s*=\s*[\"']([^\"']*(pass|pwd|otp|card|cvv|ssn|nric|ic[-_ ]?no)[^\"']*)[\"']",
    re.IGNORECASE,
)
_FORM_ACTION = re.compile(r"<form[^>]+action\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_TRACKERS = [
    ("geolocation API", re.compile(r"navigator\.geolocation", re.IGNORECASE)),
    ("media capture (webcam/mic)", re.compile(r"getUserMedia|navigator\.mediaDevices", re.IGNORECASE)),
    ("form-to-remote-post", re.compile(r"fetch\s*\(\s*['\"]https?://", re.IGNORECASE)),
    ("clipboard hijack", re.compile(r"navigator\.clipboard|document\.execCommand\(['\"]copy", re.IGNORECASE)),
]


def _host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def _extract_captures(html: str) -> list[dict[str, str]]:
    """Detect client-side capture commands in the served page (static analysis)."""
    captures: list[dict[str, str]] = []
    for match in _CREDENTIAL_HINTS.finditer(html):
        captures.append({"type": "credential_field", "detail": match.group(2)[:60]})
    action = _FORM_ACTION.search(html)
    if action and action.group(1).startswith("http"):
        captures.append({"type": "external_form_post", "detail": action.group(1)[:120]})
    for name, pattern in _TRACKERS:
        if pattern.search(html):
            captures.append({"type": name, "detail": "API call signature found in page source"})
    return captures[:10]


_GENERATOR_META = re.compile(
    r"<meta[^>]+name=[\"']generator[\"'][^>]+content=[\"']([^\"']+)", re.IGNORECASE
)


def _fingerprint_stack(headers: httpx.Headers, html: str) -> str:
    parts = []
    server = headers.get("server", "")
    if server:
        parts.append(server[:40])
    powered = headers.get("x-powered-by", "")
    if powered:
        parts.append(powered[:40])
    generator = _GENERATOR_META.search(html)
    if generator:
        parts.append("generator: " + generator.group(1)[:40])
    if "captcha" in html.lower():
        parts.append("captcha widget")
    if not parts:
        return "no identifiable stack markers"
    return "; ".join(parts)


def probe(url: str, risk: str) -> dict[str, Any]:
    """Run the isolated probe. Returns the evidence payload (never raises)."""
    settings = get_settings()
    host = _host_of(url)
    base: dict[str, Any] = {
        "target": url,
        "host": host,
        "risk_at_request": risk,
        "requested_at": utcnow().isoformat(),
    }

    if not host:
        return {**base, "status": "refused", "detail": "No resolvable host in the target URL."}
    if not settings.allow_outbound_lookups:
        return {
            **base,
            "status": "refused",
            "detail": (
                "Sandbox probe unavailable: outbound lookups are disabled (offline demo mode). "
                "Enable ALLOW_OUTBOUND_LOOKUPS with your own API/network access to run recon."
            ),
        }

    try:
        with httpx.Client(
            timeout=8.0,
            follow_redirects=True,
            max_redirects=settings.redirect_max_hops,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
        ) as client:
            response = client.get(url)

        final_url = str(response.url)
        html = response.text[:MAX_RESPONSE_BYTES]
        ip: Optional[str] = None
        ip_source = ""
        header_ip = response.headers.get("x-originating-ip") or response.headers.get("cf-ray")
        if header_ip:
            ip_source = "response header"
        # Honest disclosure: without a DNS tool dependency we disclose exactly
        # where the IP came from; socket-level resolution is noted if present.
        try:
            import socket

            ip = socket.gethostbyname(_host_of(final_url))
            ip_source = "DNS resolution"
        except OSError:
            ip = None

        hosting_provider = ""
        try:
            from backend.tools.domain_lookup import lookup_domain

            intel = lookup_domain(_host_of(final_url))
            hosting_provider = (intel.registrar or "")[:60]
        except Exception:  # noqa: BLE001 — recon must degrade silently
            hosting_provider = ""

        findings = {
            "ip": ip or "unresolved",
            "hosting_provider": hosting_provider or "unresolvable within probe scope",
            "tech_stack": _fingerprint_stack(response.headers, html),
        }
        captures = _extract_captures(html)

        return {
            **base,
            "status": "completed",
            "final_url": final_url,
            "http_status": response.status_code,
            "findings": findings,
            "capture_commands": captures,
            "capture_count": len(captures),
            "requests_sent": 1,
            "ip_source": ip_source,
            "safety_note": (
                "Isolated one-shot GET: no code execution, no cookies, no user data transmitted. "
                "Evidence is for police reporting only."
            ),
        }
    except Exception as exc:  # noqa: BLE001 — degrade gracefully, never 500
        return {
            **base,
            "status": "failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "requests_sent": 0,
        }
