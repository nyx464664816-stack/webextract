# WebExtract measured results

Generated 2026-10-26T00:56:57Z from `results/summary.json` (every number below is computed by `analyze.py` from the raw JSON in `results/raw/` and the logs in `results/*.jsonl|json`). Test pages: 10 public pages that allow this kind of access (see `urls.json` for each page's robots.txt note). User-Agent: `webextract-integration/benchmark-1`.

## 1. Sandbox runs (Base Sepolia test USDC; same extraction function and server process as production, only the payment step differs)

Each of the 10 pages was fetched 4 times per endpoint (40 runs per endpoint). Success = HTTP 200 with non-empty markdown. Latency counts successful runs only and **includes the testnet payment settlement**, so it is not the latency of the free or the production path. p95 is the nearest-rank percentile.

| Endpoint | Runs | Success | Success rate | Median ms | p95 ms | Field checks passed |
|---|---|---|---|---|---|---|
| markdown | 40 | 38 | 95.0% | 3130 | 5605 | 75/75 |
| extract | 40 | 40 | 100.0% | 3041 | 4231 | 212/212 |

Failed runs (kept in the success rate):

- markdown, 1x: `httpbin-html:HTTP 422  {"error":"upstream_error","message":"target site returned HTTP 502; no`
- markdown, 1x: `sts-forms:HTTP 402  {"error":"payment_required","reason":"settlement_failed","message":"Pa`

Which record counts: for each page, endpoint and run number the first attempt that was not an HTTP 429 (rate-limit) answer. The sandbox allows 20 requests per minute, so the script waits and resends after a 429. If the first attempt failed for another reason it still counts, even if a resend later succeeded. 84 records were logged; 4 are not counted:

- 2026-10-26T00:18:35Z (UTC): sts-forms extract run 1, HTTP 429 (rate limit, resent after a wait)
- 2026-10-26T00:18:36Z (UTC): httpbin-html markdown run 1, HTTP 429 (rate limit, resent after a wait)
- 2026-10-26T00:18:36Z (UTC): httpbin-html extract run 1, HTTP 429 (rate limit, resent after a wait)
- 2026-10-26T00:19:03Z (UTC): sts-forms markdown run 1, HTTP 200 (later attempt; the first attempt was counted)

Field completeness = checks passed / checks that apply. Checks are simple and independent of WebExtract (ground truth is parsed straight from each page's HTML in `ground_truth.py`): page h1 and longest paragraph appear in the markdown; every table cell appears in the markdown; for `extract` also: `metadata.title` equals the page title, number of tables and rows per table, and for the product page `product.name` and `product.price`. They show that content is present, not that every field a user might want is present.

### Per page (successful runs only)

| Page | Endpoint | Runs | OK | Median ms | p95 ms |
|---|---|---|---|---|---|
| example | markdown | 4 | 4 | 3702 | 5154 |
| example | extract | 4 | 4 | 2412 | 4364 |
| books-home | markdown | 4 | 4 | 3264 | 3724 |
| books-home | extract | 4 | 4 | 3342 | 3665 |
| books-product | markdown | 4 | 4 | 3070 | 4960 |
| books-product | extract | 4 | 4 | 2616 | 3221 |
| books-mystery | markdown | 4 | 4 | 3376 | 4971 |
| books-mystery | extract | 4 | 4 | 3382 | 3542 |
| quotes | markdown | 4 | 4 | 2794 | 2913 |
| quotes | extract | 4 | 4 | 3276 | 5658 |
| wsio-product | markdown | 4 | 4 | 2860 | 4192 |
| wsio-product | extract | 4 | 4 | 2228 | 2581 |
| wsio-tables | markdown | 4 | 4 | 2966 | 5605 |
| wsio-tables | extract | 4 | 4 | 2198 | 2597 |
| sts-simple | markdown | 4 | 4 | 4350 | 6374 |
| sts-simple | extract | 4 | 4 | 4029 | 4231 |
| sts-forms | markdown | 4 | 3 | 3304 | 3432 |
| sts-forms | extract | 4 | 4 | 3586 | 3811 |
| httpbin-html | markdown | 4 | 3 | 3239 | 3558 |
| httpbin-html | extract | 4 | 4 | 3041 | 3100 |

## 2. Are failed requests charged? (REST, sandbox)

Method: the test wallet's on-chain USDC balance was read before and after the failure calls, then once more after one control call that succeeds (a successful call must show a charge, otherwise the check proves nothing).

| Case | Endpoint | HTTP | Error | Message |
|---|---|---|---|---|
| http-404 | markdown | 422 | upstream_error | target site returned HTTP 404; not charged |
| http-404 | extract | 422 | upstream_error | target site returned HTTP 404; not charged |
| dns-failure | markdown | 422 | dns_failed | DNS lookup failed |
| dns-failure | extract | 422 | dns_failed | DNS lookup failed |
| not-html-png | markdown | 415 | unsupported_type | unsupported content type: image/png; not charged |
| not-html-png | extract | 415 | unsupported_type | unsupported content type: image/png; not charged |
| private-127.0.0.1 | markdown | 400 | forbidden_host | private/internal addresses are not allowed |
| private-127.0.0.1 | extract | 400 | forbidden_host | private/internal addresses are not allowed |
| private-10.0.0.1 | markdown | 400 | forbidden_host | private/internal addresses are not allowed |
| private-10.0.0.1 | extract | 400 | forbidden_host | private/internal addresses are not allowed |

- Balance before the 10 failure calls: 18.904000 USDC; after: 18.904000 USDC; charged for failures: 0.000000 USDC.
- Control call (`https://example.com/`, markdown, HTTP 200): charged 0.002000 USDC.
- Also seen in the 80 runs above: the upstream-502 failure was answered 422 with `"charged": false`; the one testnet `settlement_failed` answered 402 with "You were not charged". These two are the response text only; the balance check covers the cases in the table.
- Server log check: the server operator compared access-log and payment-journal rows for the same minutes; the log itself is not published. Each sandbox call is two access rows (unpaid 402, then the retry). For all 10 failing calls the journal has a verify line (the payment authorisation was checked) and no settle line, and the retries are 422, 415 or 400. The control call is the only settlement in the window (22 access rows, 11 verify lines, 1 settle line). The access log does not record the target URL, so domains were matched to this list by order and status code.
- Not covered: the 10 failures were measured on the sandbox route only; it shares the extraction code with the live `/v1` route, and the docs state failed fetches are not charged. Failing URLs were not run through the paid live path, so this is not claimed as measured.

## 3. Live free path, small sample

The free quota is 20 calls per caller IP per day, shared by REST and MCP (one counter), so the sample was capped at 14 calls and stopped at the first non-200. Statuses: {'200': 13, '402': 1}. The 402 is the free quota of the calling address running out. Our outgoing address is not fixed (the reported counter went 11, 10, 9, then back to 19), so this sample does not measure the 20-call limit.

| Endpoint | n | Median ms | p95 ms |
|---|---|---|---|
| markdown | 7 | 1675 | 1874 |
| extract | 6 | 992 | 1474 |

- Live markdown identical to the sandbox markdown of the same page: 13/13.
- Live extract JSON identical to sandbox extract JSON except `fetched_at`: 6/6.
- Field checks on the live responses: 48/48.
- n is tiny (6 or 7 per endpoint); the latency numbers are a sample, and the pages may have been served from a cache. Do not compare them with the sandbox latency.

## 4. Unpaid 402 quote latency

Unpaid request to the production `/v1` endpoints (no payment header): the server answers HTTP 402 with the price. This measures only how fast the quote comes back.

| Endpoint | n | Median ms | p95 ms | Statuses |
|---|---|---|---|---|
| markdown | 5 | 765 | 786 | [402] |
| extract | 5 | 765 | 803 | [402] |

## Limits of this test

- One client location (a cloud box), a few hours of one day, 10 pages. Results from another place or time can differ.
- Sandbox latency includes testnet settlement; the quote latency has no fetching at all; the live sample is small. The three numbers answer different questions.
- Completeness checks are simple heuristics, see above.
- The sandbox and `/v1` run in the same server process and call the same extraction function; only the payment step differs. The failure test covers the sandbox route only.
- The free quota is counted per caller IP and our client IP is not fixed, so nothing here says how the limit behaves for one IP.
- No competitor was run; `competitors.md` only restates their public pages with source and date.
- Mainnet payment was not tested, and MCP payment was not tested here.
