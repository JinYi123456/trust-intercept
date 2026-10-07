"""Domain intel: WHOIS/RDAP age lookup + VirusTotal / Google Safe Browsing reputation.

Results are cached in a TTL dict so the live demo survives free-tier rate
limits (the blueprint's cached-fallback requirement). When every engine is
unavailable the intel is returned with explicit notes instead of an error, so
the synthesiser can state the uncertainty rather than failing the demo.
"""
from __future__ import annotations

import base64
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend.config import get_settings
from backend.models.case import DomainIntel, ReputationEngineResult

_cache: dict[str, tuple[float, DomainIntel]] = {}
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_domain(url: str) -> str:
    """Return the lowercase hostname of ``url`` (port and credentials stripped)."""
    try:
        netloc = urlparse(url).netloc
        host = netloc.split("@")[-1].split(":")[0]
        return host.strip().lower()
    except Exception:
        return ""


def _days_since(created: datetime) -> int:
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - created).days, 0)


def _parse_date(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# WHOIS / RDAP
# ---------------------------------------------------------------------------


def _add_whois_age(intel: DomainIntel) -> None:
    """Fill in creation date / age via python-whois, falling back to RDAP."""
    settings = get_settings()
    try:
        import whois as pywhois  # python-whois

        record = pywhois.whois(intel.domain)
        created = record.get("creation_date") if record else None
        if isinstance(created, list):
            created = created[0] if created else None
        parsed = _parse_date(created)
        if parsed is not None:
            intel.created_at = parsed.date().isoformat()
            intel.domain_age_days = _days_since(parsed)
            registrar = record.get("registrar") if record else None
            intel.registrar = str(registrar) if registrar else ""
            intel.lookup_source = "whois"
            return
        intel.notes.append("WHOIS returned no creation date; trying RDAP.")
    except Exception as exc:
        intel.notes.append(f"WHOIS lookup failed ({type(exc).__name__}); trying RDAP.")

    # RDAP fallback — free, no key needed.
    try:
        response = httpx.get(
            f"https://rdap.org/domain/{intel.domain}",
            follow_redirects=True,
            timeout=settings.outbound_timeout_seconds,
        )
        if response.status_code != 200:
            intel.notes.append(f"RDAP lookup returned HTTP {response.status_code}.")
            return
        data = response.json()
        for event in data.get("events", []):
            if event.get("eventAction") == "registration":
                parsed = _parse_date(event.get("eventDate", ""))
                if parsed is not None:
                    intel.created_at = parsed.date().isoformat()
                    intel.domain_age_days = _days_since(parsed)
                    intel.lookup_source = "rdap"
                    break
        for entity in data.get("entities", []):
            if "registrar" in (entity.get("roles") or []):
                vcard = entity.get("vcardArray") or []
                for field in (vcard[1] if len(vcard) > 1 else []):
                    if field and field[0] == "fn" and len(field) > 3:
                        intel.registrar = str(field[3])
                        break
    except Exception as exc:
        intel.notes.append(f"RDAP lookup failed: {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Reputation engines
# ---------------------------------------------------------------------------


def _virustotal_lookup(url: str) -> ReputationEngineResult:
    settings = get_settings()
    result = ReputationEngineResult(engine="virustotal")

    if not settings.virustotal_api_key:
        result.unavailable_reason = "No VirusTotal API key configured (VIRUSTOTAL_API_KEY)."
        return result
    if not settings.allow_outbound_lookups:
        result.unavailable_reason = "Outbound lookups are disabled (demo offline mode)."
        return result

    url_id = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    try:
        response = httpx.get(
            f"https://www.virustotal.com/api/v3/urls/{url_id}",
            headers={"x-apikey": settings.virustotal_api_key},
            timeout=settings.outbound_timeout_seconds,
        )
    except Exception as exc:
        result.unavailable_reason = f"Request failed: {type(exc).__name__}: {exc}"
        return result

    if response.status_code == 404:
        result.checked = True
        result.unavailable_reason = "No record yet — this URL has never been submitted to VirusTotal."
        return result
    if response.status_code == 429:
        result.unavailable_reason = "Rate limited by VirusTotal; continuing on cached/empty data."
        return result
    if response.status_code != 200:
        result.unavailable_reason = f"VirusTotal returned HTTP {response.status_code}."
        return result

    try:
        stats = (
            response.json()
            .get("data", {})
            .get("attributes", {})
            .get("last_analysis_stats", {})
        )
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values()) or 1
        result.checked = True
        result.malicious = (malicious + suspicious) > 0
        result.detail = f"{malicious + suspicious}/{total} vendors flagged this URL as malicious or suspicious."
    except Exception as exc:
        result.unavailable_reason = f"Could not parse the VirusTotal response: {exc}"
    return result


def _safe_browsing_lookup(url: str) -> ReputationEngineResult:
    settings = get_settings()
    result = ReputationEngineResult(engine="safe_browsing")

    if not settings.safe_browsing_api_key:
        result.unavailable_reason = "No Google Safe Browsing key configured (SAFE_BROWSING_API_KEY)."
        return result
    if not settings.allow_outbound_lookups:
        result.unavailable_reason = "Outbound lookups are disabled (demo offline mode)."
        return result

    body = {
        "client": {"clientId": "trust-intercept-scam-defence", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        response = httpx.post(
            f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={settings.safe_browsing_api_key}",
            json=body,
            timeout=settings.outbound_timeout_seconds,
        )
    except Exception as exc:
        result.unavailable_reason = f"Request failed: {type(exc).__name__}: {exc}"
        return result

    if response.status_code != 200:
        result.unavailable_reason = f"Google Safe Browsing returned HTTP {response.status_code}."
        return result

    try:
        matches = response.json().get("matches", [])
        result.checked = True
        result.malicious = bool(matches)
        result.detail = (
            f"{len(matches)} threat match(es) returned by Google Safe Browsing."
            if matches
            else "No threats found in Google Safe Browsing."
        )
    except Exception as exc:
        result.unavailable_reason = f"Could not parse the Safe Browsing response: {exc}"
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup_domain(url: str) -> DomainIntel:
    """Age + reputation intel for the domain behind ``url``, with TTL caching."""
    settings = get_settings()
    domain = extract_domain(url)
    intel = DomainIntel(domain=domain or url)

    if not domain:
        intel.notes.append("Could not parse a hostname from the URL.")
        return intel

    cache_key = f"{domain}|{settings.reputation_cache_ttl_seconds}"
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > now:
            cached_intel = cached[1].model_copy(deep=True)
            cached_intel.cache_hit = True
            return cached_intel

    if not settings.allow_outbound_lookups:
        intel.notes.append("Outbound lookups are disabled (demo offline mode); intel is intentionally empty.")
    else:
        _add_whois_age(intel)
        intel.reputation.append(_virustotal_lookup(url))
        intel.reputation.append(_safe_browsing_lookup(url))

    if intel.domain_age_days is None:
        intel.notes.append(f"Domain age could not be verified for {domain}.")

    if intel.reputation and all(
        (not rep.checked) or rep.unavailable_reason for rep in intel.reputation
    ):
        intel.notes.append(f"No reputation verdict was available for {domain}.")

    # Blueprint: state the conflict when tools disagree in coverage.
    new_domain = intel.domain_age_days is not None and intel.domain_age_days < 30
    vt_no_record = any(
        rep.engine == "virustotal" and rep.checked and rep.unavailable_reason
        for rep in intel.reputation
    )
    if new_domain and vt_no_record:
        intel.notes.append(
            "The domain looks very new but VirusTotal has no record of this URL yet — "
            "the evidence is thin; treat as unresolved."
        )

    with _cache_lock:
        _cache[cache_key] = (now + settings.reputation_cache_ttl_seconds, intel.model_copy(deep=True))
    return intel


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
