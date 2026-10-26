"""Shared helpers. Every request sends a User-Agent starting with webextract-integration (counted as internal traffic)."""
import json, os, re, time, pathlib
HERE = pathlib.Path(__file__).parent
RES = HERE / "results"; RAW = RES / "raw"
BASE = os.environ.get("WEBEXTRACT_BASE", "https://api.webextract.dev")
UA = "webextract-integration/benchmark-1"
URLS = json.load(open(HERE / "urls.json"))
def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def norm(s): return re.sub(r"\s+", " ", str(s or "")).strip()
def pct(sorted_vals, p):
    """nearest-rank percentile on a list of numbers"""
    v = sorted(sorted_vals); k = max(1, -(-len(v) * p // 100)); return v[int(k) - 1]
