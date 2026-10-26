# Free-path sample in one command

Two dependency-free scripts that repeat the free-path sample from the [benchmark page](https://webextract.dev/benchmark): 7 public pages, each through `/v1/markdown` and `/v1/extract`, at most 14 calls, 3 seconds apart.

```sh
python3 free_sample.py        # Python 3.8+, standard library only
node free_sample.mjs          # Node 18+, no packages
```

Pass a number to run fewer calls (`python3 free_sample.py 4`). Each line shows HTTP status, wall-clock milliseconds, the `X-Free-Remaining` header and the word count. The script stops at the first non-200 answer and exits with code 1.

- The free path is 20 calls per caller IP per day, shared with MCP, and needs the opt-in header `X-Billing: free` (the scripts send it). No wallet, no payment.
- If your traffic leaves through several addresses, the counter may be split or merged across them. Run it from one address for a clean check.
- HTTP 402 `free_limit_reached` means today's free calls from your IP are used up. The scripts do not pay.
- Latency here is the free path only. It is not comparable with the sandbox latency on the benchmark page, which includes testnet settlement.
- `WEBEXTRACT_UA` sets your own User-Agent, `WEBEXTRACT_BASE` points the scripts at another server.
