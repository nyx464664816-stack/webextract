#!/usr/bin/env python3
"""Reproduce the WebExtract free-path sample with one command (Python 3.8+, standard library only).

    python3 free_sample.py            # up to 14 calls: 7 public pages x /v1/markdown and /v1/extract
    python3 free_sample.py 4          # only the first 4 calls

It uses the free path (header `X-Billing: free`): 20 calls per caller IP per day, shared with MCP.
It stops at the first non-200 answer (HTTP 402 `free_limit_reached` means today's free calls from your IP are used up).
No wallet, no payment. Set WEBEXTRACT_BASE to use another server, WEBEXTRACT_UA to set your own User-Agent.
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev").rstrip("/")
UA = os.environ.get("WEBEXTRACT_UA", "webextract-benchmark-example/1 (python)")
PAGES = [
    "https://example.com/",
    "https://books.toscrape.com/",
    "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    "https://quotes.toscrape.com/",
    "https://webscraper.io/test-sites/tables",
    "https://www.scrapethissite.com/pages/forms/",
    "https://httpbin.org/html",
]
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 14
calls = [(ep, u) for u in PAGES for ep in ("markdown", "extract")][:limit]

print(f"{'endpoint':9} {'status':6} {'ms':>6} {'free left':>9} {'words':>6}  page")
ok = 0
for ep, page in calls:
    req = urllib.request.Request(f"{BASE}/v1/{ep}?" + urllib.parse.urlencode({"url": page}),
                                 headers={"User-Agent": UA, "X-Billing": "free"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            status, body, left = r.status, r.read(), r.headers.get("X-Free-Remaining", "-")
    except urllib.error.HTTPError as e:
        status, body, left = e.code, e.read(), e.headers.get("X-Free-Remaining", "-")
    ms = round((time.perf_counter() - t0) * 1000)
    try:
        data = json.loads(body)
    except ValueError:
        data = {}
    words = data.get("word_count", "-") if status == 200 else "-"
    print(f"{ep:9} {status:<6} {ms:>6} {left:>9} {words:>6}  {page}")
    if status != 200:
        print("stopped:", status, data.get("reason") or data.get("error") or body[:200].decode("utf-8", "replace"))
        break
    if not str(data.get("markdown", "")).strip():
        print("stopped: HTTP 200 but empty markdown"); break
    ok += 1
    time.sleep(3)
print(f"{ok} of {len(calls)} calls returned HTTP 200 with markdown.")
sys.exit(0 if ok == len(calls) else 1)
