#!/usr/bin/env python3
"""
Discover page URLs from a site's XML sitemap(s), optionally filtered by a
path prefix.

Given a sitemap URL or a site root, this resolves the sitemap(s) (via
robots.txt and common locations when a root is supplied), recursively follows
``<sitemapindex>`` entries, extracts page ``<loc>`` values, filters them by an
optional ``--prefix``, and emits the result as JSON or a plain URL list.

Used by client tracking profiles to expand a "track everything under
/section/*" intent into the concrete URL list that the drift skill needs,
without hand-listing every page.

Usage:
    python sitemap_urls.py <sitemap-or-site-url> [--prefix URL]
                           [--limit N] [--format json|text]

Examples:
    python sitemap_urls.py https://example.com/sitemap.xml
    python sitemap_urls.py https://example.com/ --prefix https://example.com/blog/
    python sitemap_urls.py https://example.com/ --prefix https://example.com/us/en/ --format text

Output (json): {"sitemaps_read": [...], "prefix": ..., "count": N,
                "truncated": bool, "urls": [...]}
Output (text): one URL per line.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from url_safety import (  # noqa: E402
    URLSafetyError,
    safe_requests_get,
    validate_url,
)

# Common sitemap locations to probe when only a site root is supplied.
_COMMON_SITEMAP_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap.xml.gz",
)

_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)
_SITEMAP_SITEMAP_RE = re.compile(r"<sitemap[\s>]", re.IGNORECASE)
_ROBOTS_SITEMAP_RE = re.compile(r"^\s*sitemap:\s*(\S+)", re.IGNORECASE | re.MULTILINE)

# Bound recursion so a malformed / self-referential sitemap index cannot loop
# or fan out without limit.
_MAX_SITEMAPS = 200


def _fetch_text(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL and return decoded text, transparently gunzipping .gz."""
    try:
        resp = safe_requests_get(url, timeout=timeout)
    except (URLSafetyError, Exception):
        return None
    if resp.status_code != 200:
        return None
    body = resp.content
    # Gzip magic bytes or .gz suffix -> decompress.
    if url.lower().endswith(".gz") or body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except OSError:
            return None
    try:
        return body.decode("utf-8", errors="replace")
    except Exception:
        return None


def discover_sitemaps(root_or_sitemap: str) -> list[str]:
    """
    Return an ordered list of candidate sitemap URLs.

    If the input already looks like a sitemap (``.xml`` / ``.xml.gz`` / contains
    "sitemap"), it is used directly. Otherwise robots.txt is checked for
    ``Sitemap:`` directives, then common locations are probed.
    """
    parsed = urlparse(root_or_sitemap)
    path = parsed.path.lower()
    if path.endswith(".xml") or path.endswith(".xml.gz") or "sitemap" in path:
        return [root_or_sitemap]

    origin = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []

    # 1) robots.txt Sitemap: directives (authoritative).
    robots = _fetch_text(urljoin(origin, "/robots.txt"))
    if robots:
        for m in _ROBOTS_SITEMAP_RE.finditer(robots):
            candidates.append(m.group(1).strip())

    # 2) Common conventional locations.
    for p in _COMMON_SITEMAP_PATHS:
        candidates.append(urljoin(origin, p))

    # De-dupe, preserve order.
    seen: set[str] = set()
    ordered: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def collect_urls(seed_sitemaps: list[str]) -> tuple[list[str], list[str]]:
    """
    Walk sitemaps (following ``<sitemapindex>`` recursively) and return
    ``(page_urls, sitemaps_read)``.
    """
    page_urls: list[str] = []
    sitemaps_read: list[str] = []
    seen_sitemaps: set[str] = set()
    seen_pages: set[str] = set()

    queue = list(seed_sitemaps)
    while queue and len(sitemaps_read) < _MAX_SITEMAPS:
        sm = queue.pop(0)
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        text = _fetch_text(sm)
        if text is None:
            continue
        sitemaps_read.append(sm)
        locs = [m.strip() for m in _LOC_RE.findall(text)]
        if _SITEMAP_SITEMAP_RE.search(text):
            # Sitemap index: <loc> entries are child sitemaps.
            for child in locs:
                if child not in seen_sitemaps:
                    queue.append(child)
        else:
            # URL set: <loc> entries are pages.
            for u in locs:
                if u not in seen_pages:
                    seen_pages.add(u)
                    page_urls.append(u)

    return page_urls, sitemaps_read


def get_urls(
    root_or_sitemap: str,
    prefix: str | None = None,
    limit: int | None = None,
) -> dict:
    """Discover, walk, filter, and cap. Returns the result dict."""
    if not validate_url(root_or_sitemap):
        return {"error": f"Unsafe or invalid URL: {root_or_sitemap}"}
    if prefix and not validate_url(prefix):
        return {"error": f"Unsafe or invalid prefix URL: {prefix}"}

    seeds = discover_sitemaps(root_or_sitemap)
    urls, sitemaps_read = collect_urls(seeds)

    if prefix:
        urls = [u for u in urls if u.startswith(prefix)]

    urls = sorted(set(urls))
    total = len(urls)
    truncated = False
    if limit is not None and total > limit:
        urls = urls[:limit]
        truncated = True

    return {
        "seed": root_or_sitemap,
        "prefix": prefix,
        "sitemaps_read": sitemaps_read,
        "count": len(urls),
        "total_matched": total,
        "truncated": truncated,
        "urls": urls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Sitemap URL or site root")
    parser.add_argument(
        "--prefix",
        default=None,
        help="Only return page URLs starting with this prefix",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of URLs to return",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    result = get_urls(args.url, prefix=args.prefix, limit=args.limit)

    if args.format == "text":
        if result.get("error"):
            print(result["error"], file=sys.stderr)
            return 1
        for u in result["urls"]:
            print(u)
        return 0

    print(json.dumps(result, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
