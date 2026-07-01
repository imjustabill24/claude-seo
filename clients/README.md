# Client Tracking Profiles

Version-controlled tracking profiles for client sites monitored with Claude SEO.

Each client lives in its own directory (`clients/<client-slug>/`) and holds:

| File | Purpose |
|------|---------|
| `profile.md` | Client overview, tracked URLs, cadence, and the exact commands to run |
| `urls.txt` | Tracked URLs — one per line, or an `@sitemap` directive (see below); `#` comments and blank lines ignored |
| `track.sh` | Convenience wrapper: runs a drift command over every URL in `urls.txt` |

### Tracking a whole section without listing pages

`urls.txt` accepts a directive line:

```
@sitemap <sitemap-or-site-url> [prefix]
```

At run time `track.sh` expands it via `scripts/sitemap_urls.py`, which discovers
the site's XML sitemap (robots.txt + common locations), follows sitemap-index
files, and returns every page URL starting with `[prefix]`. This means you track
`/section/*` by maintaining the **prefix**, not the page list — new pages are
picked up automatically. Cap expansion with `SEO_SITEMAP_LIMIT` (default 100).

> **Network policy is per-domain, not per-page.** Allowlisting `example.com`
> (or using **Full**) covers every URL on the domain; there is no per-path
> egress setting. The `@sitemap` prefix only controls *which pages get
> baselined*, not what the network permits.

## Why this exists

The drift skill stores baselines in `~/.cache/claude-seo/drift/baselines.db`,
which is **local and ephemeral** — it does not survive a fresh checkout or a
recycled cloud container. These profiles are the *durable, shareable* record of
**what** we track and **how**, so any machine (or a re-opened cloud session) can
reproduce the baseline set with one command. The captured snapshots themselves
still live in the local SQLite DB and are re-created on demand.

## Usage

```bash
# Capture baselines for every tracked URL of a client
clients/<client-slug>/track.sh baseline

# Later: compare current state to stored baselines
clients/<client-slug>/track.sh compare

# Review change history
clients/<client-slug>/track.sh history
```

`baseline` and `compare` pass `--skip-cwv` by default (no PageSpeed API key
needed). Set `SEO_DRIFT_CWV=1` to include Core Web Vitals — this requires a
Google PageSpeed API key configured for the `seo-google` skill.

## Network requirement (cloud sessions)

Fetching arbitrary client domains requires the environment's **Network access**
to be **Full** or **Custom** (with the client domain allowlisted). The default
**Trusted** level only reaches package registries and Google APIs, so client
site fetches return `403`. See the network-access section of the
[Claude Code on the web docs](https://code.claude.com/docs/en/claude-code-on-the-web).

## Adding a new client

1. `mkdir clients/<client-slug>`
2. Copy an existing `urls.txt` and `track.sh`, then edit `urls.txt`.
3. Write `profile.md` with the client overview and cadence.
