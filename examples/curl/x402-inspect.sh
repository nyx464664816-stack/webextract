#!/usr/bin/env bash
# Get the x402 payment requirements WITHOUT paying anything.
# The server answers 402 + PAYMENT-REQUIRED (x402 v2, base64 JSON) to any request without a key, payment or X-Billing: free;
# `X-Billing: x402` makes that explicit (reason x402_requested).
# Usage: ./x402-inspect.sh [extract|markdown] [url]
# Sandbox (Base Sepolia test USDC only): WEBEXTRACT_BILLING=x402-testnet ./x402-inspect.sh
set -euo pipefail
BASE="${WEBEXTRACT_BASE:-https://api.webextract.dev}"
EP="${1:-extract}"; TARGET="${2:-https://example.com}"
HDRS=$(mktemp); BODY=$(mktemp); trap 'rm -f "$HDRS" "$BODY"' EXIT
code=$(curl -sS -G -o "$BODY" -D "$HDRS" -w '%{http_code}' -H "X-Billing: ${WEBEXTRACT_BILLING:-x402}" "$BASE/v1/$EP" --data-urlencode "url=$TARGET")
echo "HTTP $code"
echo "== body"; cat "$BODY"; echo
echo "== decoded PAYMENT-REQUIRED header"
grep -i '^payment-required:' "$HDRS" | cut -d' ' -f2- | tr -d '\r\n' | base64 -d | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("x402Version:", d["x402Version"], "| resource:", d["resource"]["url"])
print(f"{"network":<14} {"amount":>7}  {"asset":<44} payTo / extra")
for a in d["accepts"]:
    print(f"{a["network"]:<14} {a["amount"]:>7}  {a["asset"]:<44} {a["payTo"]} {a.get("extra")}")
'
