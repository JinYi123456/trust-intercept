"""Module 2 — QR & Link Safety Agent.

Turns raw mechanical tool output into explainable link evidence:
* ``redirect_walker`` → the hop-by-hop chain (capped at 5 hops)
* ``domain_lookup``   → domain age (WHOIS/RDAP) + reputation engines

Then adds rule-based link flags and — when an LLM is available — one
plain-English verdict sentence in the blueprint's own style: "this link hides
its real destination behind 3 redirects and lands on a domain registered 4
days ago".
"""
from __future__ import annotations

import ipaddress
import json
import re
from urllib.parse import urlparse

from backend.agent import llm
from backend.models.case import (
    Confidence,
    Cue,
    DomainIntel,
    LinkSafetyResult,
    RedirectChain,
    RiskLevel,
    Severity,
)
from backend.tools import domain_lookup, redirect_walker

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
    "rb.gy", "shorturl.at", "ow.ly", "rebrand.ly", "tiny.cc",
}
SUSPICIOUS_TLDS = {".zip", ".mov", ".top", ".xyz", ".click", ".work", ".rest", ".country"}

SEVERITY_ORDER = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2}
RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


def extract_urls(text: str) -> list[str]:
    """Deduplicated URLs in order of first appearance."""
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,;:!?)\"'")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _flag(cue_type: str, text: str, explanation: str, severity: Severity) -> Cue:
    return Cue(cue_type=cue_type, text=text, explanation=explanation, severity=severity, source="rules")


def _rule_flags(url: str, chain: RedirectChain, intel: DomainIntel) -> list[Cue]:
    flags: list[Cue] = []
    host = domain_lookup.extract_domain(url)
    path = urlparse(url).path.lower()

    if host in URL_SHORTENERS:
        flags.append(_flag(
            "url_shortener", url,
            "A link shortener hides the true destination — expand it before trusting where it leads.",
            Severity.MEDIUM,
        ))

    try:
        ipaddress.ip_address(host)
        flags.append(_flag(
            "ip_host", url,
            "The link points at a raw IP address instead of a named domain — almost never legitimate for consumer services.",
            Severity.HIGH,
        ))
    except ValueError:
        pass

    if host.startswith("xn--") or ".xn--" in host:
        flags.append(_flag(
            "punycode_domain", url,
            "The domain uses punycode, which can visually imitate well-known brands with look-alike characters.",
            Severity.HIGH,
        ))

    if url.lower().startswith("http://"):
        flags.append(_flag(
            "no_https", url,
            "The link uses plain HTTP, so anything entered on that page is not encrypted.",
            Severity.MEDIUM,
        ))

    if intel.domain_age_days is not None and intel.domain_age_days < 30:
        flags.append(_flag(
            "brand_new_domain", intel.domain,
            f"The domain was registered {intel.domain_age_days} days ago — scam campaigns typically use freshly registered domains for a few days and then abandon them.",
            Severity.HIGH,
        ))

    if any(tld in ("." + host.rsplit(".", 1)[-1]) for tld in SUSPICIOUS_TLDS):
        flags.append(_flag(
            "suspicious_tld", intel.domain,
            "The top-level domain is frequently abused in phishing campaigns.",
            Severity.MEDIUM,
        ))

    hops = len(chain.hops)
    if hops >= 3:
        flags.append(_flag(
            "redirect_obfuscation", url,
            f"The link bounces through {hops} redirects before landing, hiding its true destination from you.",
            Severity.MEDIUM if hops < 5 else Severity.HIGH,
        ))

    for rep in intel.reputation:
        if rep.checked and rep.malicious:
            flags.append(_flag(
                "flagged_reputation",
                intel.domain,
                f"Reputation engines flagged this destination: {rep.detail}",
                Severity.HIGH,
            ))

    if path and any(word in path for word in ("login", "verify", "secure", "update", "wallet", "connect")):
        flags.append(_flag(
            "credential_landing", url,
            "The landing path suggests a login or verification page — a common place to harvest credentials.",
            Severity.MEDIUM,
        ))

    return flags


def _plain_verdict(chains: list[RedirectChain], domains: list[DomainIntel], flags: list[Cue]) -> str:
    """Deterministic fallback verdict in the blueprint's own narrative style."""
    if not chains:
        return ""
    chain = chains[0]
    intel = domains[0] if domains else None
    hops = len(chain.hops)

    if hops >= 2 and intel and intel.domain_age_days is not None:
        return (
            f"This link hides its real destination behind {hops} redirects and lands on a "
            f"domain registered {intel.domain_age_days} days ago."
        )
    if hops >= 2:
        return f"This link passes through {hops} redirects before reaching its final destination, which could not be age-verified."
    if intel and intel.domain_age_days is not None and intel.domain_age_days < 30:
        return f"The destination domain was registered only {intel.domain_age_days} days ago."
    if intel and any(rep.checked and rep.malicious for rep in intel.reputation):
        return "A reputation engine has flagged this destination as dangerous."
    if flags:
        return f"The link was checked end-to-end; {len(flags)} concern(s) were found and are listed below."
    return "The link resolves directly to its stated domain with no redirects, and no reputation engine flagged it."


def _llm_verdict(urls: list[str], chains: list[RedirectChain], domains: list[DomainIntel]) -> dict:
    """One LLM call over the RAW tool outputs. Raises LlmUnavailable if no provider."""
    answer = llm.generate(
        "link_verdict",
        {
            "urls": ", ".join(urls) or "(none)",
            "chains": json.dumps(
                [chain.model_dump(mode="json") for chain in chains], ensure_ascii=False, indent=2
            ),
            "domains": json.dumps(
                [intel.model_dump(mode="json") for intel in domains], ensure_ascii=False, indent=2
            ),
        },
    )
    return answer


def run(urls: list[str]) -> LinkSafetyResult:
    """Walk every URL, gather domain intel, and produce an explainable verdict."""
    urls = urls or []
    chains: list[RedirectChain] = []
    domains: list[DomainIntel] = []
    flags: list[Cue] = []
    notes: list[str] = []

    for url in urls[:5]:  # safety cap on URLs per case
        chain = redirect_walker.walk_redirects(url)
        chains.append(chain)
        intel = domain_lookup.lookup_domain(chain.final_url or url)
        domains.append(intel)
        flags.extend(_rule_flags(url, chain, intel))

    flags.sort(key=lambda cue: -SEVERITY_ORDER[cue.severity])

    severities = [flag.severity for flag in flags]
    if Severity.HIGH in severities:
        risk = RiskLevel.HIGH
    elif severities.count(Severity.MEDIUM) >= 2:
        risk = RiskLevel.HIGH
    elif Severity.MEDIUM in severities:
        risk = RiskLevel.MEDIUM
    else:
        risk = RiskLevel.LOW

    verdict_text = _plain_verdict(chains, domains, flags)
    llm_explained = False

    if urls:
        try:
            answer = _llm_verdict(urls, chains, domains)
            llm_flags = [
                Cue(
                    cue_type=str(item.get("cue_type", "link_flag"))[:60],
                    text=str(item.get("text", ""))[:160],
                    explanation=str(item.get("explanation", ""))[:400],
                    severity=Severity(str(item.get("severity", "medium")).lower()),
                    source="llm",
                )
                for item in answer.get("link_flags", [])
                if isinstance(item, dict) and item.get("text")
            ]
            existing = {(cue.cue_type, cue.text.lower()) for cue in flags}
            for cue in llm_flags:
                if (cue.cue_type, cue.text.lower()) not in existing:
                    flags.append(cue)
            llm_risk = answer.get("risk")
            if llm_risk in ("low", "medium", "high") and RISK_ORDER[RiskLevel(llm_risk)] > RISK_ORDER[risk]:
                risk = RiskLevel(llm_risk)
            if answer.get("verdict_text"):
                verdict_text = str(answer["verdict_text"])
            llm_explained = True
        except Exception:  # noqa: BLE001 — raw tool outputs always stand alone
            notes.append("LLM verdict unavailable — built from raw tool outputs with rule-based flags only.")

    return LinkSafetyResult(
        risk=risk,
        urls=urls,
        chains=chains,
        domains=domains,
        link_flags=flags,
        verdict_text=verdict_text,
        llm_explained=llm_explained,
        notes=notes,
    )
