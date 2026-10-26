"""RESULTS.md is generated from results/summary.json only. python analyze.py && python make_results.py"""
import json
from common import *
S = json.load(open(RES / "summary.json")); F = json.load(open(RES / "failures.json")); sb = S["sandbox"]; L = S["live_free_summary"]; Q = S["quotes_summary"]
usdc = lambda a: f"{a/1e6:.6f}"
o = []; w = o.append
w("# WebExtract measured results\n")
w(f"Generated {S['generated']} from `results/summary.json` (every number below is computed by `analyze.py` from the raw JSON in `results/raw/` and the logs in `results/*.jsonl|json`). Test pages: {len(URLS)} public pages that allow this kind of access (see `urls.json` for each page's robots.txt note). User-Agent: `{UA}`.\n")
w("## 1. Sandbox runs (Base Sepolia test USDC; same extraction function and server process as production, only the payment step differs)\n")
w("Each of the 10 pages was fetched 4 times per endpoint (40 runs per endpoint). Success = HTTP 200 with non-empty markdown. Latency counts successful runs only and **includes the testnet payment settlement**, so it is not the latency of the free or the production path. p95 is the nearest-rank percentile.\n")
w("| Endpoint | Runs | Success | Success rate | Median ms | p95 ms | Field checks passed |\n|---|---|---|---|---|---|---|")
for ep in ("markdown", "extract"):
    s = sb[ep]; w(f"| {ep} | {s['runs']} | {s['success']} | {s['success_rate']*100:.1f}% | {s['median_ms']} | {s['p95_ms']} | {s['checks_passed']}/{s['checks_total']} |")
w("\nFailed runs (kept in the success rate):\n")
for ep in ("markdown", "extract"):
    for p, n in sb[ep]["problems"]: w(f"- {ep}, {n}x: `{p}`")
if not any(sb[ep]["problems"] for ep in sb): w("- none")
rows_all = [json.loads(l) for l in open(RES / "sandbox_runs.jsonl")]; seen = set(); excl = []
for r in rows_all:
    if r.get("pacing") or r.get("status") == 429: excl.append(r); continue
    k = (r["id"], r["endpoint"], r["rep"])
    if k in seen: excl.append(r)
    seen.add(k)
w(f"\nWhich record counts: for each page, endpoint and run number the first attempt that was not an HTTP 429 (rate-limit) answer. The sandbox allows 20 requests per minute, so the script waits and resends after a 429. If the first attempt failed for another reason it still counts, even if a resend later succeeded. {len(rows_all)} records were logged; {len(excl)} are not counted:\n")
for r in excl: w(f"- {r['ts']} (UTC): {r['id']} {r['endpoint']} run {r['rep']}, HTTP {r['status']}" + (" (rate limit, resent after a wait)" if r.get("pacing") or r.get("status") == 429 else " (later attempt; the first attempt was counted)"))
w("\nField completeness = checks passed / checks that apply. Checks are simple and independent of WebExtract (ground truth is parsed straight from each page's HTML in `ground_truth.py`): page h1 and longest paragraph appear in the markdown; every table cell appears in the markdown; for `extract` also: `metadata.title` equals the page title, number of tables and rows per table, and for the product page `product.name` and `product.price`. They show that content is present, not that every field a user might want is present.\n")
w("### Per page (successful runs only)\n\n| Page | Endpoint | Runs | OK | Median ms | p95 ms |\n|---|---|---|---|---|---|")
for u in URLS:
    for ep in ("markdown", "extract"):
        p = S["per_url"][u["id"]][ep]; w(f"| {u['id']} | {ep} | {p['runs']} | {p['ok']} | {p.get('median_ms','-')} | {p.get('p95_ms','-')} |")
w("\n## 2. Are failed requests charged? (REST, sandbox)\n")
w("Method: the test wallet's on-chain USDC balance was read before and after the failure calls, then once more after one control call that succeeds (a successful call must show a charge, otherwise the check proves nothing).\n")
w("| Case | Endpoint | HTTP | Error | Message |\n|---|---|---|---|---|")
for c in F["cases"]: w(f"| {c['case']} | {c['endpoint']} | {c['status']} | {c['error']} | {c['message']} |")
w(f"\n- Balance before the {len(F['cases'])} failure calls: {usdc(F['balance_before_atomic'])} USDC; after: {usdc(F['balance_after_failures_atomic'])} USDC; charged for failures: {usdc(F['failures_charged_atomic'])} USDC.")
w(f"- Control call (`{F['control']['url']}`, {F['control']['endpoint']}, HTTP {F['control']['status']}): charged {usdc(F['control_charged_atomic'])} USDC.")
w("- Also seen in the 80 runs above: the upstream-502 failure was answered 422 with `\"charged\": false`; the one testnet `settlement_failed` answered 402 with \"You were not charged\". These two are the response text only; the balance check covers the cases in the table.")
w("- Server log check: the server operator compared access-log and payment-journal rows for the same minutes; the log itself is not published. Each sandbox call is two access rows (unpaid 402, then the retry). For all 10 failing calls the journal has a verify line (the payment authorisation was checked) and no settle line, and the retries are 422, 415 or 400. The control call is the only settlement in the window (22 access rows, 11 verify lines, 1 settle line). The access log does not record the target URL, so domains were matched to this list by order and status code.")
w("- Not covered: the 10 failures were measured on the sandbox route only; it shares the extraction code with the live `/v1` route, and the docs state failed fetches are not charged. Failing URLs were not run through the paid live path, so this is not claimed as measured.\n")
w("## 3. Live free path, small sample\n")
w(f"The free quota is 20 calls per caller IP per day, shared by REST and MCP (one counter), so the sample was capped at 14 calls and stopped at the first non-200. Statuses: {L['statuses']}. The 402 is the free quota of the calling address running out. Our outgoing address is not fixed (the reported counter went 11, 10, 9, then back to 19), so this sample does not measure the 20-call limit.\n")
w("| Endpoint | n | Median ms | p95 ms |\n|---|---|---|---|")
for ep in ("markdown", "extract"):
    s = L["latency"][ep]; w(f"| {ep} | {s['n']} | {s['median_ms']} | {s['p95_ms']} |")
same_md = sum(1 for c in L["per_call"] if c.get("markdown_identical")); same_js = [c for c in L["per_call"] if "json_identical_except_fetched_at" in c]
w(f"\n- Live markdown identical to the sandbox markdown of the same page: {same_md}/{len(L['per_call'])}.")
w(f"- Live extract JSON identical to sandbox extract JSON except `fetched_at`: {sum(c['json_identical_except_fetched_at'] for c in same_js)}/{len(same_js)}.")
w(f"- Field checks on the live responses: {sum(c['checks_passed'] for c in L['per_call'])}/{sum(c['checks_total'] for c in L['per_call'])}.")
w("- n is tiny (6 or 7 per endpoint); the latency numbers are a sample, and the pages may have been served from a cache. Do not compare them with the sandbox latency.\n")
w("## 4. Unpaid 402 quote latency\n")
w("Unpaid request to the production `/v1` endpoints (no payment header): the server answers HTTP 402 with the price. This measures only how fast the quote comes back.\n")
w("| Endpoint | n | Median ms | p95 ms | Statuses |\n|---|---|---|---|---|")
for ep in ("markdown", "extract"):
    s = Q[ep]; w(f"| {ep} | {s['n']} | {s['median_ms']} | {s['p95_ms']} | {s['statuses']} |")
w("\n## Limits of this test\n")
w("- One client location (a cloud box), a few hours of one day, 10 pages. Results from another place or time can differ.\n- Sandbox latency includes testnet settlement; the quote latency has no fetching at all; the live sample is small. The three numbers answer different questions.\n- Completeness checks are simple heuristics, see above.\n- The sandbox and `/v1` run in the same server process and call the same extraction function; only the payment step differs. The failure test covers the sandbox route only.\n- The free quota is counted per caller IP and our client IP is not fixed, so nothing here says how the limit behaves for one IP.\n- No competitor was run; `competitors.md` only restates their public pages with source and date.\n- Mainnet payment was not tested, and MCP payment was not tested here.")
open(HERE / "RESULTS.md", "w").write("\n".join(o) + "\n")
