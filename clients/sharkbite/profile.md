# SharkBite (US / EN) — Tracking Profile

| Field | Value |
|-------|-------|
| **Client** | SharkBite |
| **Primary URL** | https://www.sharkbite.com/us/en |
| **Market / locale** | United States, English (`/us/en`) |
| **Industry** | Plumbing products / manufacturer (push-to-connect fittings, PEX) — *to confirm* |
| **Tracking type** | SEO drift baseline (on-page SEO regression monitoring) |
| **Storage** | Local SQLite — `~/.cache/claude-seo/drift/baselines.db` (ephemeral) |
| **Set up** | 2026-07-01 |

## Tracked URLs

See [`urls.txt`](./urls.txt). Rather than listing every page, it tracks the
whole `/us/en/` section via a sitemap directive:

```
https://www.sharkbite.com/us/en                                   # section root (explicit)
@sitemap https://www.sharkbite.com/ https://www.sharkbite.com/us/en/   # everything under /us/en/
```

The `@sitemap <url> [prefix]` line is expanded at run time by
`scripts/sitemap_urls.py`: it discovers the site's XML sitemap (via robots.txt
and common locations), follows any sitemap-index files, and returns every page
whose URL starts with the prefix. So new pages under `/us/en/` are picked up
automatically on each run — no manual list to maintain.

> **Prefix note:** `/us/en/` (trailing slash) matches descendants but not the
> bare `/us/en` homepage, so the homepage is listed explicitly above.
> **Volume:** expansion is capped by `SEO_SITEMAP_LIMIT` (default 100). A large
> site can have thousands of URLs — raise the cap deliberately, since each URL
> is a fetch on every baseline/compare run.

## Cadence

| Action | When |
|--------|------|
| **Baseline refresh** | Before any known site deploy/migration, and monthly as a rolling "known good" |
| **Compare** | Weekly, and immediately after any deploy |
| **History review** | When investigating a ranking/traffic drop |

## Commands

Run from the repo root. The wrapper iterates every URL in `urls.txt`:

```bash
clients/sharkbite/track.sh baseline    # capture "known good" snapshots
clients/sharkbite/track.sh compare     # diff current state vs. baselines
clients/sharkbite/track.sh history     # show change history
```

Or a single page directly:

```bash
python3 scripts/drift_baseline.py https://www.sharkbite.com/us/en --skip-cwv
python3 scripts/drift_compare.py  https://www.sharkbite.com/us/en --skip-cwv
python3 scripts/drift_history.py  https://www.sharkbite.com/us/en
```

## Notes

- **Egress:** requires **Full** or **Custom** network access in cloud sessions
  (Trusted returns `403` for `sharkbite.com`). See `clients/README.md`.
- **Ephemeral DB:** baselines don't survive a recycled container. For
  restart-proof tracking, consider a committed snapshot export or wiring up
  Google Search Console (`/seo google`) as a follow-up.
- **What drift captures:** title, meta description, canonical, robots, H1–H3,
  JSON-LD schema, Open Graph, status code, and content hashes. Optionally Core
  Web Vitals with `SEO_DRIFT_CWV=1` (needs a PageSpeed API key).
