#!/usr/bin/env bash
# WebExtract curl quickstart. Free tier: 50 calls/day per IP, no key.
# Usage: ./quickstart.sh [url]       (set WEBEXTRACT_KEY to use prepaid credits)
set -euo pipefail
BASE="${WEBEXTRACT_BASE:-https://api.webextract.dev}"
TARGET="${1:-https://example.com}"
AUTH=(); [ -n "${WEBEXTRACT_KEY:-}" ] && AUTH=(-H "Authorization: Bearer ${WEBEXTRACT_KEY}")

echo "== balance (free calls left today, or prepaid credits)"
curl -sS "${AUTH[@]}" "$BASE/v1/balance"; echo

echo "== /v1/markdown (Markdown only; 0.4 credit / \$0.002 x402)"
# -G + --data-urlencode encodes the target URL safely (needed when it has its own ?query&params)
curl -sS -G "${AUTH[@]}" -D /dev/stderr "$BASE/v1/markdown" --data-urlencode "url=$TARGET" 2> >(grep -iE '^(HTTP|x-free|x-credits)' >&2); echo

echo "== /v1/extract (Markdown + metadata/product/tables; 1 credit / \$0.005 x402)"
curl -sS -G "${AUTH[@]}" "$BASE/v1/extract" --data-urlencode "url=$TARGET" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ("final_url","word_count","metadata","product")}, indent=2, ensure_ascii=False)[:1500]); print("tables:", len(d.get("tables") or []))'
