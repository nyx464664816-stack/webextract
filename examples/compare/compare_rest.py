"""Same product page, two WebExtract results side by side: Markdown (/v1/markdown) vs structured JSON (/v1/extract).

    pip install requests
    python compare_rest.py [page-url]

Free tier (20 calls/day per IP) is used unless WEBEXTRACT_KEY (prepaid Bearer key) is set.
Optional: WEBEXTRACT_UA to label your own traffic."""
import json, os, sys, requests

BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev")
URL = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
headers = {"Authorization": f"Bearer {os.environ['WEBEXTRACT_KEY']}"} if os.environ.get("WEBEXTRACT_KEY") else {"X-Billing": "free"}
if os.environ.get("WEBEXTRACT_UA"): headers["User-Agent"] = os.environ["WEBEXTRACT_UA"]

md = requests.get(f"{BASE}/v1/markdown", params={"url": URL}, headers=headers, timeout=60); md.raise_for_status()
ex = requests.get(f"{BASE}/v1/extract", params={"url": URL}, headers=headers, timeout=60); ex.raise_for_status()
md, ex = md.json(), ex.json()

print("=== /v1/markdown  ($0.002 or 0.4 credit): text for an LLM to read ===")
print(md["markdown"][:600], "…" if len(md["markdown"]) > 600 else "")
print(f"[title={md['title']!r} word_count={md['word_count']}]\n")
p = ex.get("product") or {}
print("=== /v1/extract  ($0.005 or 1 credit): the same markdown PLUS fixed-schema fields a program can use ===")
print(json.dumps({"product": {k: p.get(k) for k in ("name", "price", "currency", "availability", "rating", "sku", "gtin")},
                  "price_warnings": (p.get("price_detail") or {}).get("warnings"),
                  "tables": [{"headers": t["headers"], "rows": t["rows"][:3]} for t in ex.get("tables", [])][:1],
                  "metadata": {k: ex["metadata"].get(k) for k in ("title", "language", "canonical_url")}}, ensure_ascii=False, indent=2))
print("\nsame markdown in both:", md["markdown"] == ex["markdown"], "| extract fields:", sorted(ex))
