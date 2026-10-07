"""Redirect-chain walker — follows each hop manually, capped at 5 hops.

The walker never downloads page bodies (it streams and immediately closes each
response) and detects redirect loops by remembering every URL it has seen.
"""
from __future__ import annotations

from urllib.parse import urljoin

import httpx

from backend.config import get_settings
from backend.models.case import RedirectChain, RedirectHop

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
USER_AGENT = "TRUST//INTERCEPT-Scam-Defence/1.0 (hackathon demo; explains redirect chains to users)"


def walk_redirects(start_url: str, max_hops: "int | None" = None) -> RedirectChain:
    """Trace the redirect chain from ``start_url`` and return a RedirectChain."""
    settings = get_settings()
    chain = RedirectChain(start_url=start_url, final_url=start_url)

    if not start_url.lower().startswith(("http://", "https://")):
        chain.error = "URL must start with http:// or https://."
        return chain

    if not settings.allow_outbound_lookups:
        chain.error = "Outbound lookups are disabled (demo offline mode); redirect chain not followed."
        return chain

    max_hops = settings.redirect_max_hops if max_hops is None else max_hops
    visited = [start_url]
    url = start_url

    with httpx.Client(
        follow_redirects=False,
        timeout=settings.outbound_timeout_seconds,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for index in range(max_hops):
            try:
                request = client.build_request("GET", url)
                response = client.send(request, stream=True)
            except httpx.HTTPError as exc:
                chain.error = (
                    f"Request failed at hop {index}: {type(exc).__name__}: {exc}"
                )
                return chain
            except Exception as exc:  # TLS errors and other unexpected failures
                chain.error = f"Request failed at hop {index}: {exc}"
                return chain

            hop = RedirectHop(index=index, url=str(response.url), status_code=response.status_code)

            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("location", "")
                hop.location = location
                response.close()
                chain.hops.append(hop)

                if not location:
                    chain.error = (
                        f"Hop {index} returned HTTP {response.status_code} without a Location header."
                    )
                    chain.final_url = str(response.url)
                    return chain

                next_url = urljoin(str(response.url), location)
                if next_url in visited:
                    chain.loop_detected = True
                    chain.final_url = next_url
                    return chain

                visited.append(next_url)
                url = next_url
                continue

            # Landing page reached — we have the final URL without reading the body.
            response.close()
            chain.hops.append(hop)
            chain.final_url = str(response.url)
            return chain

    # The loop ran out of hops without reaching a landing page.
    chain.truncated = True
    chain.final_url = url
    return chain
