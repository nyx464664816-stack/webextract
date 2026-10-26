# Verify WebExtract yourself

These scripts produced the numbers in `RESULTS.md` (and on the [benchmark page](https://webextract.dev/benchmark)). Raw responses are in `results/raw/`, per-request logs in `results/sandbox_runs.jsonl`, `results/failures.json`, `results/quotes.json`, `results/live_free.json`.

## Rules we followed
- Only public pages that allow this kind of access (`urls.json`, with each robots.txt note).
- Volume runs go to the Base Sepolia **sandbox** (`/sandbox/v1/*`, test USDC, no real money). The production free quota (20 calls per caller IP per day) is used for a capped sample only. Nothing was paid on mainnet.
- Every number in `RESULTS.md` is computed from raw files by `analyze.py` + `make_results.py`; none was typed by hand.
- Competitors: `competitors.md` only copies their public pages, with source link and date. We did not run them.

## What you need
- Python 3 (we ran 3.13.5) and these packages (versions we used: x402 2.25.0, eth-account 0.14.0, requests 2.34.2, beautifulsoup4 4.15.0, lxml 6.1.3).
- For the sandbox scripts only: a Base Sepolia **test** wallet that holds some test USDC (from a Base Sepolia USDC faucet). Use a throwaway key that has never held real funds; the scripts register only the Base Sepolia network, so they cannot sign for another chain. Never put a mainnet key in `X402_TESTNET_PRIVATE_KEY`.
- The scripts that call the live free path or ask for quotes need no wallet.

## Run it
```sh
python -m venv venv
venv/bin/pip install requests eth_account x402 beautifulsoup4 lxml
cd <this directory>
venv/bin/python ground_truth.py     # reads each page's HTML directly; independent of WebExtract
venv/bin/python run_quotes.py       # unpaid requests -> 402 price quotes (no payment, no free call used)
venv/bin/python run_live_free.py    # at most 14 free-path calls, stops at the first non-200
export X402_TESTNET_PRIVATE_KEY=<your Base Sepolia TEST key>
venv/bin/python run_sandbox.py 4    # 4 reps x 10 pages x 2 endpoints = 80 calls
venv/bin/python run_failures.py     # bad URLs + on-chain test-USDC balance before/after
venv/bin/python analyze.py          # -> results/summary.json
venv/bin/python make_results.py     # -> RESULTS.md
venv/bin/python page/build_page.py  # optional: rebuilds page/benchmark.html from the same JSON
```
Run all of them once, in this order: `analyze.py` needs `ground_truth.json` and the sandbox results, `make_results.py` also needs `failures.json`, and `page/build_page.py` also needs `quotes.json` and `live_free.json`.

## Things worth knowing
- **Time:** the 80 sandbox calls took about 12 minutes for us (calls are 7 s apart on purpose). The other scripts take a minute or two.
- **Limits:** the sandbox allows 20 requests per minute and 300 per day per IP, and an unpaid plus a paid request each count, so one call is two requests. The scripts pace themselves and retry only on HTTP 429.
- **Resuming and starting over:** `run_sandbox.py` skips calls whose raw file already exists and appends to `results/sandbox_runs.jsonl`. To repeat a run from scratch, delete `results/sandbox_runs.jsonl` and `results/raw/sandbox/` first, otherwise old rows are counted again.
- **Free quota is per IP:** `run_live_free.py` uses your own IP's 20 free calls for the day. If your traffic leaves through several addresses, the counter may not behave like one number, and a 402 `free_limit_reached` simply ends the sample. Run it from a single address if you want a clean check.
- **Timing:** sandbox latency includes the testnet settlement and must not be compared with the free-path or quote latency.
- **Another server:** set `WEBEXTRACT_BASE` to point the scripts at a different base URL.
- **User-Agent:** `common.py` sets `UA`. Change it to something that identifies you.
- **Public data:** the files under `results/raw/` are the exact responses we got, so you can diff them against your own run (`fetched_at` differs on every call).
