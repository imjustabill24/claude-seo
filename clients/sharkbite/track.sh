#!/usr/bin/env bash
#
# Run an SEO drift command over every tracked SharkBite URL in urls.txt.
#
# Usage:
#   clients/sharkbite/track.sh [baseline|compare|history]   (default: baseline)
#
# Environment:
#   SEO_DRIFT_CWV=1   Include Core Web Vitals (needs a PageSpeed API key).
#                     Ignored for 'history'.
#
set -euo pipefail

CMD="${1:-baseline}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
URLS_FILE="$HERE/urls.txt"

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

if [[ ! -f "$URLS_FILE" ]]; then
  echo "No urls.txt found at $URLS_FILE" >&2
  exit 1
fi

count=0
while IFS= read -r line || [[ -n "$line" ]]; do
  # Strip leading/trailing whitespace.
  url="${line#"${line%%[![:space:]]*}"}"
  url="${url%"${url##*[![:space:]]}"}"
  [[ -z "$url" ]] && continue          # blank line
  [[ "$url" == \#* ]] && continue      # comment
  echo "=== $CMD: $url ==="
  python3 "$REPO_ROOT/scripts/$SCRIPT" "$url" "${FLAGS[@]}"
  count=$((count + 1))
done < "$URLS_FILE"

echo "Done. Processed $count URL(s)."
