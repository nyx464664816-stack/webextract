#!/usr/bin/env python3
"""WebExtract public status probe. Read-only: never pays, never uses free quota, never touches /buy/*.
Usage: python3 status/probe.py OUT_DIR   (reads OUT_DIR/history.json if present, writes status.json, history.json, index.html)"""
import json, os, sys, ssl, socket, time, base64, html, datetime as dt, urllib.request, urllib.error

API = "https://api.webextract.dev"
SITE = "https://webextract.dev"
MAINNETS = {"eip155:8453": "Base", "eip155:137": "Polygon", "eip155:42161": "Arbitrum", "eip155:43114": "Avalanche",
            "eip155:10": "Optimism", "eip155:480": "World Chain", "eip155:143": "Monad"}
TESTNET = "eip155:84532"
KST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "webextract-status-probe/1.0 (+https://status.webextract.dev)"}
HISTORY_MAX = 2016  # about 7 days at 5-minute intervals

def req(url, method="GET", body=None, headers=None, timeout=20):
    h = dict(UA, **(headers or {}))
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read(200000), round((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(200000), round((time.time() - t0) * 1000)
    except Exception as e:
        return None, {}, str(e).encode(), round((time.time() - t0) * 1000)

def hget(hdrs, name):
    for k, v in hdrs.items():
        if k.lower() == name.lower(): return v
    return None

def check_page(name, url, must_contain=None):
    st, h, b, ms = req(url)
    ok = st == 200 and (must_contain is None or must_contain.encode() in b)
    return {"name": name, "url": url, "ok": ok, "status": st, "ms": ms,
            "detail": "" if ok else f"HTTP {st}" + ("" if st != 200 else f", missing {must_contain!r}")}

def check_paid(name, path):
    url = f"{API}{path}?url=https://example.com"
    st, h, b, ms = req(url)  # no X-Billing, no payment header -> must be a well-formed 402
    r = {"name": name, "url": f"{API}{path}", "status": st, "ms": ms, "ok": False, "detail": ""}
    if st != 402:
        r["detail"] = f"expected 402, got HTTP {st}"; return r
    reason = hget(h, "X-Payment-Reason")
    pr = hget(h, "PAYMENT-REQUIRED")
    try:
        j = json.loads(base64.b64decode(pr + "==="))
        nets = sorted({a["network"] for a in j.get("accepts", [])})
    except Exception:
        r["detail"] = "402 without a valid PAYMENT-REQUIRED header"; return r
    missing = [MAINNETS[n] for n in MAINNETS if n not in nets]
    if TESTNET in nets: r["detail"] = "testnet listed on mainnet endpoint"
    elif missing: r["detail"] = "missing networks: " + ", ".join(missing)
    else: r["ok"] = True
    r["reason"] = reason
    r["networks"] = [MAINNETS.get(n, n) for n in nets]
    return r

def check_health():
    url = f"{API}/health"
    st, h, b, ms = req(url)
    r = {"name": "API health", "url": url, "ok": False, "status": st, "ms": ms, "detail": ""}
    try: j = json.loads(b)
    except Exception: j = None
    if st != 200 or not isinstance(j, dict) or j.get("ok") is not True:
        r["detail"] = f"HTTP {st}" + ("" if st != 200 else ", ok != true"); return r
    nets = j.get("x402_networks")
    if isinstance(nets, list):  # present after the 2026-10-21 price-provenance patch
        missing = [MAINNETS[n] for n in MAINNETS if n not in nets]
        if TESTNET in nets: r["detail"] = "testnet listed in x402_networks"; return r
        if missing: r["detail"] = "x402_networks missing: " + ", ".join(missing); return r
        r["networks"] = [MAINNETS.get(n, n) for n in nets]
    r["ok"] = True
    return r

def check_mcp():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode()
    st, h, b, ms = req(f"{API}/mcp", "POST", body, {"Content-Type": "application/json",
                                                     "Accept": "application/json, text/event-stream"})
    return {"name": "MCP endpoint", "url": f"{API}/mcp", "ok": st == 200, "status": st, "ms": ms,
            "detail": "" if st == 200 else f"HTTP {st}"}

def check_tls(host):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as s, ctx.wrap_socket(s, server_hostname=host) as ss:
            exp = dt.datetime.strptime(ss.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)
        days = (exp - dt.datetime.now(dt.timezone.utc)).days
        return {"name": f"TLS {host}", "ok": days >= 14, "days_left": days,
                "expires_utc": exp.isoformat(), "detail": "" if days >= 14 else f"certificate expires in {days} days"}
    except Exception as e:
        return {"name": f"TLS {host}", "ok": False, "detail": str(e)[:200]}

def render(status, history):
    rows = []
    for c in status["checks"]:
        name = c["name"]
        hist = [h["checks"].get(name) for h in history if name in h.get("checks", {})]
        up = round(100 * sum(1 for x in hist if x) / len(hist), 2) if hist else None
        extra = c.get("detail") or (", ".join(c["networks"]) if c.get("networks") else "")
        if "days_left" in c and not c.get("detail"): extra = f'{c["days_left"]} days left'
        rows.append(f'<tr><td>{"🟢" if c["ok"] else "🔴"}</td><td>{html.escape(name)}</td>'
                    f'<td>{c.get("ms","")}{" ms" if "ms" in c else ""}</td><td>{"" if up is None else f"{up}%"}</td>'
                    f'<td>{html.escape(extra)}</td></tr>')
    overall = "All systems operational" if status["ok"] else "Some checks are failing"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WebExtract status</title><link rel="alternate" type="application/json" href="status.json">
<style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #eee;padding:.5rem;text-align:left;font-size:.95rem}}
.banner{{padding:1rem;border-radius:8px;background:{"#e8f7ee" if status["ok"] else "#fdecea"};font-weight:600}}</style></head><body>
<h1>WebExtract status</h1><div class="banner">{overall}</div>
<p>Last checked {html.escape(status["checked_at_utc"])} (UTC). Checks run about every 5 minutes from GitHub Actions.
Paid endpoints are healthy when they return a well-formed x402 <code>402 Payment Required</code> listing all supported mainnets.
Machine-readable: <a href="status.json">status.json</a> · <a href="history.json">history.json</a></p>
<table><tr><th></th><th>Check</th><th>Latency</th><th>Uptime (7d)</th><th>Detail</th></tr>{"".join(rows)}</table>
<p><a href="https://webextract.dev">webextract.dev</a></p></body></html>"""

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "site"
    os.makedirs(out, exist_ok=True)
    checks = [
        check_page("Website", f"{SITE}/"),
        check_health(),
        check_paid("/v1/extract (x402)", "/v1/extract"),
        check_paid("/v1/markdown (x402)", "/v1/markdown"),
        check_mcp(),
        check_page("OpenAPI spec", f"{API}/openapi.json"),
        check_page("x402 discovery", f"{API}/.well-known/x402"),
        check_tls("api.webextract.dev"),
        check_tls("webextract.dev"),
    ]
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    status = {"service": "WebExtract", "ok": all(c["ok"] for c in checks),
              "checked_at_utc": now.isoformat().replace("+00:00", "Z"), "checks": checks}
    hp = os.path.join(out, "history.json")
    try: history = json.load(open(hp))
    except Exception: history = []
    history.append({"t": status["checked_at_utc"], "checks": {c["name"]: c["ok"] for c in checks}})
    history = history[-HISTORY_MAX:]
    json.dump(status, open(os.path.join(out, "status.json"), "w"), indent=2)
    json.dump(history, open(hp, "w"))
    open(os.path.join(out, "index.html"), "w").write(render(status, history))
    print(json.dumps({"ok": status["ok"], "failing": [c["name"] for c in checks if not c["ok"]]}))

if __name__ == "__main__":
    main()
