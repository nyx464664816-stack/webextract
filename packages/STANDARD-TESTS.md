# LangChain standard tests: 2026-10-21 20:16–20:26 KST

## Python `langchain-webextract` (PyPI) + `langchain-tests` 1.1.9 (langchain-core 1.6.12, Python 3.13)

| Suite | File | Mode | Result |
|---|---|---|---|
| `ToolsUnitTests` × 2 tools (6 standard tests each, incl. `test_init_from_env` with `WEBEXTRACT_API_KEY`) | `tests/unit_tests/test_standard.py` | `--disable-socket` | **12/12 pass** |
| Own unit tests | `tests/unit_tests/test_tools.py` | `--disable-socket` | **9/9 pass** |
| `ToolsIntegrationTests`, offline: extract_url 200, page_markdown 200, extract_url 402 `free_limit_reached` (5 tests each) | `tests/integration_tests/test_standard_offline.py` | `--disable-socket`, httpx.MockTransport | **15/15 pass** |
| `ToolsIntegrationTests`, live sandbox (Base Sepolia test USDC, sync `x402_requests` + async `x402HttpxClient`, `on_error="raise"`), plus 1 extra success check per tool | `tests/integration_tests/test_standard_sandbox.py` | opt-in `WEBEXTRACT_SANDBOX_TESTS=1` | **12/12 pass** on the final run, 20:24:16–20:26:14 KST |

The final sandbox run made 10 paid test calls, and there are exactly 10 settlements from the payer 0xFD9B…468a in that window on Base Sepolia USDC (5 × 0.002 + 5 × 0.005, via `eth_getLogs`). Earlier sandbox attempts and what they showed:
1. 20:18:52, `on_error="return"` (the default): 12/12 green, but the standard tests can't tell success from an error JSON. So I switched the sandbox suite to `on_error="raise"`.
2. 20:19:57: 3 failed with **429 "Sandbox limit: 20/minute"**. Every x402 call is 2 HTTP requests (the unpaid 402, then the signed retry). Another process on this box was paying from the same testnet wallet every ~30 s at the same time (visible on-chain from 20:08), and the limit is per IP. Fixed by pacing the live tests (7 s, `WEBEXTRACT_SANDBOX_PACE_S`).
3. 20:21:50: 11/12. One **402 `settlement_failed`** from the testnet facilitator (verified, not settled, not charged). Fixed in the clients with `settlement_retries`/`settlementRetries` = 1 (see below).
4. 20:24:16: 12/12 ✅

## LangChain.js (`@webextract/langchain` on npm)

`@langchain/standard-tests` is **not on npm** (404). In the langchainjs repo it's `internal/standard-tests` with `"private": true`, and it only covers chat models (`unit_tests/chat_models.ts`, `integration_tests/chat_models.ts`). It has no tool tests.
So `js/langchain-webextract/test/standard.test.mjs` ports the Python tool checks (init, has_name, input schema, schema matches example, invoke with ToolCall → `ToolMessage`, invoke/batch without ToolCall must not throw, init from env) over 2 tools × (200, 402): **30/30 pass**, and the own tests are 6/6.

## Interface changes the standard tests caused
1. **`test_init_from_env`** expects the tool to read its key from the environment. I added `WEBEXTRACT_API_KEY` as a fallback to both core clients (JS + Python). It's ignored when a payment client is passed or billing isn't `key`. The Python tools also gained `api_key: SecretStr` (default from env), `billing` and `base_url` fields.
2. **Live run, `settlement_failed`**: the core clients now retry this reason once by default (`settlementRetries` / `settlement_retries`, 0 = off). The payment wrapper signs a fresh payment and the server says it was not charged. No other error is retried.
3. **Sandbox 429**: no API change. The 20/min limit is effectively 10 paid calls/min. This is documented in the test file and should go in the docs.
