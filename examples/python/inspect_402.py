"""Step 1 (no wallet, no payment): get WebExtract's 402 and parse it with the official x402 SDK."""
import os, sys, httpx
from x402.http.utils import decode_payment_required_header

BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev")
endpoint = sys.argv[1] if len(sys.argv) > 1 else "extract"
target = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"

# X-Billing: x402 skips the free tier so we always get the 402 (otherwise the first 50 calls/day are free).
r = httpx.get(f"{BASE}/v1/{endpoint}", params={"url": target}, headers={"X-Billing": "x402"}, timeout=30)
print("HTTP", r.status_code)
if r.status_code != 402:
    sys.exit(f"expected 402, got {r.status_code}: {r.text[:300]}")
pr = decode_payment_required_header(r.headers["payment-required"])  # pydantic model (x402 v2)
print(f"x402Version={pr.x402_version} resource={pr.resource.url}")
for a in pr.accepts:
    print(f"  {a.scheme:5} {a.network:13} amount={a.amount:>5} (= ${int(a.amount)/1e6:.3f}) asset={a.asset} payTo={a.pay_to} extra={a.extra}")
body = r.json()
print("reason:", body.get("reason"), "| message:", body.get("message"))  # x402_requested | free_limit_reached | invalid_payment | unsupported_network
