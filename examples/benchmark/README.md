# Verify WebExtract yourself

These scripts produced the numbers in `RESULTS.md`. Raw responses are in `results/raw/`, per-request logs in `results/sandbox_runs.jsonl`, `results/failures.json`, `results/quotes.json`, `results/live_free.json`.

## Rules we followed
- Only public pages that allow this kind of access (`urls.json`, with each robots.txt note).
- Volume runs go to the Base Sepolia **sandbox** (`/sandbox/v1/*`, test USDC, no real money). The production free quota (20 calls per caller IP per day) is used for a capped sample only. Nothing was paid on mainnet.
- Every number in `RESULTS.md` is computed from raw files by `analyze.py` + `make_results.py`; none was typed by hand.
- Competitors: `competitors.md` only copies their public pages, with source link and date. We did not run them.

## Run it
```sh
python -m venv venv && venv/bin/pip install requests eth_account x402 beautifulsoup4 lxml
python ground_truth.py            # reads each page's HTML directly; independent of WebExtract
python run_quotes.py              # unpaid requests -> 402 price quotes (free)
python run_live_free.py           # <= 14 free-path calls, stops at the first non-200
X402_TESTNET_PRIVATE_KEY=<a Base Sepolia TEST key you control> python run_sandbox.py 4   # 4 reps x 10 pages x 2 endpoints
X402_TESTNET_PRIVATE_KEY=... python run_failures.py   # bad URLs + on-chain balance check
python analyze.py && python make_results.py && python page/build_page.py
```
Sandbox limit: 20 requests per minute and 300 per day per IP; an unpaid and a paid request each count. The scripts pace themselves.

Set your own User-Agent in `common.py` (`UA`).
