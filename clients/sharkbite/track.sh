#!/usr/bin/env bash
#
# Run an SEO drift command over every tracked SharkBite URL in urls.txt.
#
# urls.txt lines may be:
#   * a page URL                          -> processed directly
#   * "@sitemap <url> [prefix]"           -> expanded via scripts/sitemap_urls.py
#                                            into every page under [prefix]
#   * blank / "# comment"                 -> ignored
#
# Usage:
#   clients/sharkbite/track.sh [baseline|compare|history]   (default: baseline)
#
# Environment:
#   SEO_DRIFT_CWV=1      Include Core Web Vitals (needs a PageSpeed API key).
#                        Ignored for 'history'.
#   SEO_SITEMAP_LIMIT=N  Cap URLs expanded per @sitemap directive (default: 100).
#
set -euo pipefail

CMD="${1:-baseline}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
URLS_FILE="$HERE/urls.txt"
SITEMAP_LIMIT="${SEO_SITEMAP_LIMIT:-100}"

case "$CMD" in
  baseline) SCRIPT="drift_baseline.py" ;;
  compare)  SCRIPT="drift_compare.py" ;;
  history)  SCRIPT="drift_history.py" ;;
  *) echo "Unknown command: '$CMD' (use baseline|compare|history)" >&2; exit 1 ;;
esac

# --skip-cwv applies to baseline/compare only; opt in via SEO_DRIFT_CWV=1.
FLAGS=()
if [[ "$CMD" != "history" && "${SEO_DRIFT_CWV:-0}" != "1" ]]; then
  FLAGS+=(--skip-cwv)
fi

[[ -f "$URLS_FILE" ]] || { echo "No urls.txt found at $URLS_FILE" >&2; exit 1; }

count=0

run_one() {
  local url="$1"
  echo "=== $CMD: $url ==="
  python3 "$REPO_ROOT/scripts/$SCRIPT" "$url" "${FLAGS[@]}"
  count=$((count + 1))
}

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

while IFS= read -r line || [[ -n "$line" ]]; do
  line="$(trim "$line")"
  [[ -z "$line" ]] && continue          # blank line
  [[ "$line" == \#* ]] && continue      # comment

  if [[ "$line" == @sitemap* ]]; then
    # Parse: @sitemap <url> [prefix]
    read -r _kw sm_url sm_prefix _rest <<< "$line"
    if [[ -z "${sm_url:-}" ]]; then
      echo "Skipping malformed @sitemap directive: $line" >&2
      continue
    fi
    echo "--- expanding sitemap: $sm_url (prefix: ${sm_prefix:-none}, limit: $SITEMAP_LIMIT) ---"
    prefix_args=()
    [[ -n "${sm_prefix:-}" ]] && prefix_args=(--prefix "$sm_prefix")
    # Feed discovered URLs into the same processing loop.
    while IFS= read -r discovered; do
      [[ -z "$discovered" ]] && continue
      run_one "$discovered"
    done < <(python3 "$REPO_ROOT/scripts/sitemap_urls.py" "$sm_url" \
               "${prefix_args[@]}" --limit "$SITEMAP_LIMIT" --format text)
    continue
  fi

  run_one "$line"
done < "$URLS_FILE"

echo "Done. Processed $count URL(s)."
