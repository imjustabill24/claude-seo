"""
Tests for scripts/sitemap_urls.py.

Exercise sitemap-index recursion, prefix filtering, dedup/sort, limit
truncation, robots.txt discovery, and gzip decompression — all with the
network fetch layer mocked so no outbound request is made.
"""

from __future__ import annotations

import gzip
import os
import sys
from unittest.mock import patch

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import sitemap_urls  # noqa: E402


INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://ex.com/sm-us.xml</loc></sitemap>
  <sitemap><loc>https://ex.com/sm-ca.xml</loc></sitemap>
</sitemapindex>"""

US = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://ex.com/us/en</loc></url>
  <url><loc>https://ex.com/us/en/products</loc></url>
  <url><loc>https://ex.com/us/en/support</loc></url>
  <url><loc>https://ex.com/global/about</loc></url>
</urlset>"""

CA = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://ex.com/ca/fr/produits</loc></url>
</urlset>"""

ROBOTS = "User-agent: *\nSitemap: https://ex.com/sitemap.xml\n"

_PAGES = {
    "https://ex.com/robots.txt": ROBOTS,
    "https://ex.com/sitemap.xml": INDEX,
    "https://ex.com/sm-us.xml": US,
    "https://ex.com/sm-ca.xml": CA,
}


def _fake_fetch(url, timeout=30):
    return _PAGES.get(url)


def test_discovers_sitemap_from_robots():
    with patch.object(sitemap_urls, "_fetch_text", _fake_fetch):
        seeds = sitemap_urls.discover_sitemaps("https://ex.com/")
    assert seeds[0] == "https://ex.com/sitemap.xml"


def test_direct_sitemap_url_is_used_verbatim():
    seeds = sitemap_urls.discover_sitemaps("https://ex.com/custom-sitemap.xml")
    assert seeds == ["https://ex.com/custom-sitemap.xml"]


def test_index_recursion_and_prefix_filter():
    with patch.object(sitemap_urls, "_fetch_text", _fake_fetch):
        r = sitemap_urls.get_urls("https://ex.com/", prefix="https://ex.com/us/en/")
    # Bare /us/en (no trailing slash) is excluded; global/ and ca/ excluded.
    assert r["urls"] == [
        "https://ex.com/us/en/products",
        "https://ex.com/us/en/support",
    ]
    assert set(r["sitemaps_read"]) == {
        "https://ex.com/sitemap.xml",
        "https://ex.com/sm-us.xml",
        "https://ex.com/sm-ca.xml",
    }


def test_no_prefix_returns_all_sorted_deduped():
    with patch.object(sitemap_urls, "_fetch_text", _fake_fetch):
        r = sitemap_urls.get_urls("https://ex.com/")
    assert r["count"] == 5
    assert r["urls"] == sorted(r["urls"])


def test_limit_truncates_and_reports_total():
    with patch.object(sitemap_urls, "_fetch_text", _fake_fetch):
        r = sitemap_urls.get_urls("https://ex.com/", prefix="https://ex.com/us/en", limit=2)
    assert r["count"] == 2
    assert r["truncated"] is True
    assert r["total_matched"] == 3


def test_rejects_unsafe_url():
    r = sitemap_urls.get_urls("http://169.254.169.254/sitemap.xml")
    assert "error" in r


def test_gzip_sitemap_is_decompressed():
    raw = gzip.compress(US.encode("utf-8"))

    def fake_get(url, timeout=30):
        from types import SimpleNamespace
        return SimpleNamespace(status_code=200, content=raw)

    with patch.object(sitemap_urls, "safe_requests_get", fake_get):
        text = sitemap_urls._fetch_text("https://ex.com/sm.xml.gz")
    assert "us/en/products" in text
