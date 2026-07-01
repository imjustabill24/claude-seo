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

See [`urls.txt`](./urls.txt). Currently the confirmed page is the US/EN
homepage. Add priority pages (top category/product pages, key landing pages)
to `urls.txt` as they're confirmed — one URL per line.

> ⚠️ Only the homepage is confirmed. Placeholder priority pages are commented
> out in `urls.txt` so they aren't fetched until verified (avoids baselining
> 404s). Uncomment and correct them once the real paths are known.

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
