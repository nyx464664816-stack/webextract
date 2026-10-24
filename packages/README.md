# WebExtract SDK packages (npm and PyPI: published 0.1.1)

Published: npm `@webextract/sdk`, `@webextract/ai-sdk`, `@webextract/langchain` 0.1.0 on 2026-10-21 (20:38–20:47 KST, manual) and 0.1.1 on 2026-10-25 (04:31–04:32 KST, `publish-npm.yml` with provenance); PyPI `webextract-sdk`, `langchain-webextract` 0.1.0 on 2026-10-21 (21:04–21:05 KST) and 0.1.1 on 2026-10-25 (04:03 KST), both via `publish-pypi.yml`.

| Registry | Package | Directory | What it is | Runtime deps |
|---|---|---|---|---|
| npm | `@webextract/sdk` | `js/webextract` | Core JS/TS client (ESM + .d.ts), Node ≥ 20.3 / edge | none |
| npm | `@webextract/ai-sdk` | `js/webextract-ai-sdk` | Vercel AI SDK tools `extractUrl`, `pageMarkdown` (zod) | `@webextract/sdk`; peers `ai` ^5‖^6‖^7, `zod` ^3.25.76‖^4.1.8 |
| npm | `@webextract/langchain` | `js/langchain-webextract` | LangChain.js tools `extract_url`, `page_markdown` | `@webextract/sdk`; peers `@langchain/core` ^0.3‖^1, `zod` |
| PyPI | `webextract-sdk` (import `webextract`) | `python/webextract` | Python core client (sync `WebExtract` + `AsyncWebExtract`) | `httpx`; extra `[x402]` |
| PyPI | `langchain-webextract` | `python/langchain-webextract` | LangChain Python tools `WebExtractExtractUrl`, `WebExtractPageMarkdown` | `webextract-sdk`, `langchain-core` |

Rules shared by every package:
- **They never touch private keys.** x402 is done by a paying fetch/client that the user builds (`@x402/fetch`, or `x402HttpxClient` / `x402_requests` in Python) and passes in as `paymentFetch` / `payment_client`.
- Billing modes are `key` (Bearer), `free` (`X-Billing: free`, the default), `x402`, and `x402-testnet` (sandbox).
- Every request is `GET /v1/{extract,markdown}?url=`.
- Errors: `PaymentRequiredError` (402 + `reason`), `TargetFetchError` (422/451/... never charged), `InvalidRequestError`, `AuthenticationError`, `RateLimitError`, `ConnectionError`.

## Dev commands

```bash
cd js && npm ci && npm run build && npm test                 # all mocked
cd python && .venv/bin/python -m pytest -q --disable-socket --allow-unix-socket webextract/tests && (cd langchain-webextract && ../.venv/bin/python -m pytest -q --disable-socket --allow-unix-socket tests/unit_tests tests/integration_tests)
./check-artifacts.sh                                         # lists every file in dist-local/*, fails on secrets/.env/HTML
```

Publishing is covered in `PUBLISHING.md`, and the release workflows are `.github/workflows/publish-npm.yml` and `.github/workflows/publish-pypi.yml` at the repo root.
