"""Builds benchmark.html (single file) from ../results/summary.json, failures.json, quotes.json, live_free.json and ../urls.json.
Every number on the page is read from those files; nothing is typed in by hand.   python build_page.py -> benchmark.html"""
import json, html, pathlib, time
H = pathlib.Path(__file__).resolve().parent; B = H.parent; R = B / "results"
S = json.load(open(R / "summary.json")); F = json.load(open(R / "failures.json")); Q = json.load(open(R / "quotes.json")); LF = json.load(open(R / "live_free.json")); U = json.load(open(B / "urls.json"))
REPO = "https://github.com/nyx464664816-stack/webextract/tree/main/examples/benchmark"
RAW = "https://github.com/nyx464664816-stack/webextract/blob/main/examples/benchmark"
e = html.escape; usdc = lambda a: f"{a/1e6:.6f}"
sb = S["sandbox"]; L = S["live_free_summary"]; qs = S["quotes_summary"]
t_first = min(r["ts"] for r in (json.loads(l) for l in open(R / "sandbox_runs.jsonl"))); t_last = max(r["ts"] for r in LF)
def kst(ts):  # UTC 'YYYY-MM-DDTHH:MM:SSZ' -> KST string
    t = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone + 9 * 3600; return time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
n_runs = sb["markdown"]["runs"] + sb["extract"]["runs"]
def tbl(head, rows, cls=""):
    return f'<table{cls}><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>"
o = []; w = o.append
w(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Measured results: WebExtract on 10 public pages</title>
<meta name="description" content="Success rate, response time and field checks for WebExtract /v1/markdown and /v1/extract on 10 public pages, with scripts and raw JSON so you can rerun it.">
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 16px;color:#222}}pre,code{{background:#f4f4f4;border-radius:4px}}code{{padding:1px 4px}}pre{{padding:12px;overflow:auto}}table{{border-collapse:collapse;margin:8px 0 16px;display:block;overflow-x:auto}}td,th{{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top;font-size:15px}}th{{background:#fafafa}}.sub{{color:#666}}.note{{background:#fff8e1;padding:10px 14px;border-radius:6px}}.num td:nth-child(n+3){{text-align:right}}footer{{margin-top:40px;color:#666;font-size:14px}}details{{margin:8px 0}}summary{{cursor:pointer}}</style></head><body>
<p><a href="/">← WebExtract</a> · <a href="/docs">Docs</a> · <a href="/try">Try it</a></p>
<h1>Measured results: WebExtract on 10 public pages</h1>
<div class="note"><b>Read this first.</b> Test date {kst(t_first)[:10]} (KST); runs between {kst(t_first)[11:]} and {kst(t_last)[11:]} KST. <b>One client</b>: a single cloud-hosted machine, so results from your network will differ. <b>Sample</b>: 10 pages, 4 runs per page per endpoint, {n_runs} sandbox calls, plus {L['calls']} calls on the live free path. <b>Sandbox latency includes the testnet payment settlement</b>, so it is not the latency you see on the free or the mainnet path. <b>We did not run any competitor.</b> <b>We did not test mainnet payments or paying through MCP.</b> Competitor facts below are copied from their public pages, each with a link and the date we read it. The sandbox and the live <code>/v1</code> route run in the same server process and call the same extraction function; only the payment step differs. Every number here is computed by a script from the raw files linked at the bottom, and you can rerun it.</div>
<h2>1. Sandbox runs</h2>
<p>The 10 pages were fetched through <code>/sandbox/v1/markdown</code> and <code>/sandbox/v1/extract</code>, which call the same extraction function as <code>/v1</code> in the same server process (only the payment step differs: Base Sepolia test USDC), so the volume costs no real money and uses no free quota. Success means HTTP 200 with non-empty markdown. Latency counts successful runs only; p95 is the nearest-rank percentile. Failed runs are kept in the success rate.</p>""")
w(tbl(["Endpoint", "Runs", "Succeeded", "Success rate", "Median ms", "p95 ms", "Field checks passed"], [[ep, sb[ep]["runs"], sb[ep]["success"], f"{sb[ep]['success_rate']*100:.1f}%", sb[ep]["median_ms"], sb[ep]["p95_ms"], f"{sb[ep]['checks_passed']}/{sb[ep]['checks_total']}"] for ep in ("markdown", "extract")], ' class="num"'))
import re
def fmt(p):
    pid, rest = p.split(":", 1); st = re.search(r"HTTP (\d+)", rest); er = re.search(r'"error":"(\w+)"', rest); rs = re.search(r'"reason":"(\w+)"', rest)
    return f"page {e(pid)}: HTTP {st.group(1) if st else '?'}" + (f", error <code>{er.group(1)}</code>" if er else "") + (f", reason <code>{rs.group(1)}</code>" if rs else "")
probs = [f"<li>{ep}, {n}×: {fmt(p)}</li>" for ep in ("markdown", "extract") for p, n in sb[ep]["problems"]]
w("<p>Failed runs:</p><ul>" + ("".join(probs) or "<li>none</li>") + "</ul>")
w("""<p><b>Field completeness</b> is the share of simple checks that passed. The checks do not use WebExtract: the expected values are parsed straight from each page's HTML (<code>ground_truth.py</code>). For both endpoints: the page's h1 and longest paragraph appear in the markdown, and every table cell appears in the markdown. For <code>extract</code> also: <code>metadata.title</code> equals the page title, the number of tables and rows per table match, and on the product page <code>product.name</code> and <code>product.price</code> match. These checks show that the content is present; they do not show that every field you might want is present.</p>""")
rows_all = [json.loads(l) for l in open(R / "sandbox_runs.jsonl")]; seen = set(); excl = []
for r in rows_all:
    if r.get("pacing") or r.get("status") == 429: excl.append(r); continue
    k = (r["id"], r["endpoint"], r["rep"])
    if k in seen: excl.append(r)
    seen.add(k)
w(f"<p><b>Which record counts.</b> For each page, endpoint and run number we count the first attempt that was not an HTTP 429 (rate-limit) answer. The sandbox allows 20 requests per minute, so the script waits and resends after a 429. If the first attempt failed for another reason, it still counts as the result, even if a resend later succeeded (this happened once, see the failed runs above). {len(rows_all)} records were logged; {len(excl)} are not counted and are listed here:</p>")
w(tbl(["Time (KST)", "Page", "Endpoint", "Run", "HTTP", "Why it is not counted"], [[kst(r["ts"]) + r["ts"][16:19].replace("Z", ""), e(r["id"]), r["endpoint"], r["rep"], r["status"], "HTTP 429 rate-limit answer; the request was resent after a wait" if r.get("pacing") or r.get("status") == 429 else "a later attempt; the first attempt for this page, endpoint and run number is the one counted"] for r in excl]))
w("<details><summary>Per page results</summary>" + tbl(["Page", "Kind", "Endpoint", "Runs", "OK", "Median ms", "p95 ms"], [[f'<a href="{e(u["url"])}">{e(u["id"])}</a>', e(u["kind"]), ep, S["per_url"][u["id"]][ep]["runs"], S["per_url"][u["id"]][ep]["ok"], S["per_url"][u["id"]][ep].get("median_ms", "-"), S["per_url"][u["id"]][ep].get("p95_ms", "-")] for u in U for ep in ("markdown", "extract")], ' class="num"') + "<p class=\"sub\">Each page is public and its robots.txt does not forbid the path; the note for each page is in <code>urls.json</code>. With 4 runs per cell, the per-page p95 is just the slowest run.</p></details>")
w(f"""<h2>2. Are failed fetches charged?</h2>
<p><b>Sandbox, measured.</b> We read the test wallet's on-chain USDC balance, made {len(F['cases'])} calls that must fail (a missing page, a host that does not resolve, a non-HTML file, two private addresses; both endpoints each), read the balance again, then made one successful control call and read it a third time. The control must show a charge, otherwise the check proves nothing.</p>""")
w(tbl(["Case", "Endpoint", "HTTP", "Error code", "Message"], [[e(c["case"]), c["endpoint"], c["status"], e(c["error"] or ""), e(c["message"])] for c in F["cases"]]))
w(f"""<ul><li>Balance before the failing calls: {usdc(F['balance_before_atomic'])} USDC. After: {usdc(F['balance_after_failures_atomic'])} USDC. Charged for the failing calls: <b>{usdc(F['failures_charged_atomic'])} USDC</b>.</li>
<li>Control call (<code>{e(F['control']['url'])}</code>, {F['control']['endpoint']}, HTTP {F['control']['status']}): charged {usdc(F['control_charged_atomic'])} USDC.</li>
<li>Among the {n_runs} runs above, an upstream HTTP 502 was answered 422 with <code>"charged": false</code>, and one testnet settlement failure was answered 402 with "You were not charged". Those two are response text only; they are not balance-checked.</li></ul>
<p><b>Server log check.</b> The server operator compared the access-log and payment-journal rows for the same minutes. The log itself is not published. Each sandbox call appears as two access rows: an unpaid 402 first, then the retry with the payment. For all 10 failing calls the journal has a <code>verify</code> line (the payment authorisation was checked) and no <code>settle</code> line, and the 10 retries are 422, 415 or 400. The one control call is the only settlement in the window (22 access rows, 11 verify lines, 1 settle line). The access log does not record the target URL, so the domains were matched to our list by order and by status code.</p>
<p><b>Live <code>/v1</code> route.</b> The 10 failures were measured on the sandbox route only; it shares the extraction code with the live route, and the <a href="/docs">docs</a> state that failed fetches are not charged. We did not run failing URLs through the paid live path, so this page does not present that as measured.</p>
<h2>3. Live free path, small sample</h2>
<p>The free tier is 20 calls per caller IP per day, shared by REST and MCP, one counter (see the <a href="/docs">docs</a>). The counter is per caller address: an IPv4 address counts on its own, an IPv6 address counts by its /48 prefix, and a client that uses both IPv4 and IPv6 is counted as two callers. The sample was capped at {L['calls']} calls and stopped at the first non-200. Statuses: {e(', '.join(f'{k}: {v}' for k, v in L['statuses'].items()))}. The 402 is the free quota of the calling address running out, which is the documented behaviour. Our machine's outgoing address is not fixed (the counter the server reported went 11, 10, 9, then back up to 19), so this sample does not measure the 20-call limit.</p>""")
w(tbl(["Endpoint", "n", "Median ms", "p95 ms"], [[ep, L["latency"][ep]["n"], L["latency"][ep]["median_ms"], L["latency"][ep]["p95_ms"]] for ep in ("markdown", "extract")], ' class="num"'))
pc = L["per_call"]; sj = [c for c in pc if "json_identical_except_fetched_at" in c]
w(f"""<ul><li>Live markdown identical to the sandbox markdown for the same page: {sum(1 for c in pc if c.get('markdown_identical'))}/{len(pc)}.</li><li>Live <code>extract</code> JSON identical to the sandbox JSON except <code>fetched_at</code>: {sum(c['json_identical_except_fetched_at'] for c in sj)}/{len(sj)}.</li><li>Field checks on the live responses: {sum(c['checks_passed'] for c in pc)}/{sum(c['checks_total'] for c in pc)}.</li></ul>
<p class="sub">With 6 or 7 calls per endpoint these latencies are a sample, not a benchmark, and a page may have been served from a cache. Do not compare them with the sandbox numbers.</p>
<h2>4. Price quote latency (no payment)</h2>
<p>An unpaid request to the live <code>/v1</code> endpoints is answered with HTTP 402 and the price options, without fetching the page. This is how fast the quote comes back, {len(Q)//2} requests per endpoint.</p>""")
w(tbl(["Endpoint", "n", "Median ms", "p95 ms", "HTTP status"], [[ep, qs[ep]["n"], qs[ep]["median_ms"], qs[ep]["p95_ms"], ", ".join(map(str, qs[ep]["statuses"]))] for ep in ("markdown", "extract")], ' class="num"'))
w("""<h2>5. Other tools, from their own public pages</h2>
<p>We did not run these tools and publish no numbers for them. "Not found" means the page we read does not say. Prices and limits change, so check the linked pages. All pages were read on 2026-10-26 (KST).</p>""")
JINA = '<a href="https://jina.ai/reader/">jina.ai/reader</a>, read 2026-10-26'; FC = '<a href="https://www.firecrawl.dev/pricing">firecrawl.dev/pricing</a> and <a href="https://docs.firecrawl.dev/introduction">docs.firecrawl.dev/introduction</a>, read 2026-10-26'
W = f'<a href="{REPO}/results/quotes.json">quotes.json</a>'
w(tbl(["", "WebExtract", f"Jina Reader<br><span class=sub>source: {JINA}</span>", f"Firecrawl<br><span class=sub>source: {FC}</span>"], [
 ["Account or API key needed to start", "No (free opt-in, or pay per call)", "Rate-limit table on their page, Reader API row: 20 RPM \"w/o API Key\", 500 RPM \"w/ Free API Key\", 500 RPM \"w/ Paid API Key\", 5000 RPM \"w/ Premium API Key\"", "Docs, \"Get started\": \"No account or API key is required for this request.\" and \"Add an API key when you need higher limits.\""],
 ["Markdown output", "yes, <code>/v1/markdown</code>", "yes, <code>r.jina.ai/&lt;url&gt;</code>", "yes, <code>formats: [\"markdown\"]</code>"],
 ["Structured JSON", "fixed schema in <code>/v1/extract</code>: <code>product</code>, <code>tables</code>, <code>metadata</code>", "their FAQ: \"Use the x-json-schema header with a JSON schema definition, or use x-instruction header with natural language instructions. Both features work with ReaderLM-v2\"", "\"structured JSON\" format (their docs); pricing page: \"the JSON, Question, and Highlight formats add 4 credits per page\""],
 ["How it is priced", f"per call: $0.002 markdown, $0.005 extract (the x402 quote, see {W}); prepaid credits also exist", "tokens: the Reader API row says \"Count the number of tokens in the output response\"; the token price is not on the page we read", "credits: 1 credit per scraped page; plans from Free (1,000 credits per month, \"no card\") to Scale; pricing page: \"we add credits in 5 USD increments\" on paid plans"],
 ["Payment methods", "USDC through x402 on 7 networks; card (Stripe) for prepaid credits", "FAQ: \"Payments are processed through Stripe, supporting a variety of payment methods including credit cards, Google Pay, and PayPal\"; x402: not found", "FAQ: Stripe (cards, PayPal); sold on AWS Marketplace and Google Cloud Marketplace; x402: not found"],
 ["Failed requests", "Sandbox: not charged, measured above. Live: see section 2", "FAQ: \"No, tokens are not deducted for failed requests.\"", "FAQ: \"A scrape that returns no result is not charged. A page that responds with an error status such as 403 or 404 is still returned to you and costs 1 credit.\""],
 ["Free allowance", "20 calls per caller IP per day, REST and MCP share one counter (REST needs the opt-in header; details in the docs)", "FAQ: new users get an auto-generated API key with free tokens; without a key the limit above is 20 RPM (a rate limit, not a quota)", "Free plan: 1,000 credits per month"]]))
w(f"""<h2>Limits of this test</h2>
<ul><li>One client location, one day, 10 pages that are friendly to scraping practice (static or simple pages). Pages that need JavaScript, block bots or change often are not in this set.</li>
<li>The sandbox latency includes testnet settlement, the quote latency includes no fetching, and the live sample is small. The three numbers answer different questions.</li>
<li>The completeness checks are simple heuristics (described in section 1).</li>
<li>The free quota is counted per caller IP, and our client's outgoing IP is not fixed, so the live sample says nothing about how the 20-call limit behaves for one IP.</li>
<li>The sandbox and <code>/v1</code> run in the same server process and call the same extraction function; only the payment step differs. The failure test covers the sandbox route only.</li>
<li>No competitor was run. No mainnet payment and no payment through MCP was tested.</li></ul>
<h2>Check it yourself</h2>
<p>Everything is in the repository: <a href="{REPO}">examples/benchmark</a>.</p>
<ul><li><a href="{RAW}/RESULTS.md">RESULTS.md</a>, the same tables as this page in text form</li>
<li>Raw sandbox responses: <a href="{REPO}/results/raw/sandbox">results/raw/sandbox</a>; per-call log <a href="{RAW}/results/sandbox_runs.jsonl">sandbox_runs.jsonl</a></li>
<li>Failure test: <a href="{RAW}/results/failures.json">failures.json</a> (script <a href="{RAW}/run_failures.py">run_failures.py</a>)</li>
<li>Live free sample: <a href="{RAW}/results/live_free.json">live_free.json</a> and <a href="{REPO}/results/raw/live">results/raw/live</a> (script <a href="{RAW}/run_live_free.py">run_live_free.py</a>)</li>
<li>Price quotes: <a href="{RAW}/results/quotes.json">quotes.json</a> (script <a href="{RAW}/run_quotes.py">run_quotes.py</a>)</li>
<li>Expected values: <a href="{RAW}/results/ground_truth.json">ground_truth.json</a> (script <a href="{RAW}/ground_truth.py">ground_truth.py</a>); all numbers: <a href="{RAW}/results/summary.json">summary.json</a> (script <a href="{RAW}/analyze.py">analyze.py</a>)</li></ul>
<pre>python run_quotes.py        # free: unpaid requests, answered 402 with the price
python run_live_free.py     # at most 14 calls on the free path
X402_TESTNET_PRIVATE_KEY=&lt;a Base Sepolia test key you own&gt; python run_sandbox.py 4
X402_TESTNET_PRIVATE_KEY=... python run_failures.py
python analyze.py &amp;&amp; python make_results.py</pre>
<p class="sub">Use only a testnet key. The scripts register the Base Sepolia network only, so they cannot sign a mainnet payment. Set your own User-Agent in <code>common.py</code>.</p>
<footer><a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · <a href="/refunds">Refunds</a> · Operated by TAINCHENG, L.L.C.</footer></body></html>""")
(H / "benchmark.html").write_text("\n".join(o), encoding="utf-8"); print("wrote", H / "benchmark.html", sum(len(x) for x in o))
