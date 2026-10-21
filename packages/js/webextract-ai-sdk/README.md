# @webextract/ai-sdk

[Vercel AI SDK](https://ai-sdk.dev) tools for [WebExtract](https://webextract.dev):

- `extractUrl`: clean Markdown plus fixed-schema JSON (metadata, product and price with `price_detail`, tables). $0.005 or 1 credit.
- `pageMarkdown`: clean Markdown only. $0.002 or 0.4 credit.

```bash
npm i @webextract/ai-sdk ai zod
```

```ts
import { generateText, stepCountIs } from "ai";
import { extractUrl, pageMarkdown } from "@webextract/ai-sdk";

const { text } = await generateText({
  model: "openai/gpt-5-mini",
  prompt: "What does https://web-scraping.dev/product/1 cost?",
  tools: { extractUrl: extractUrl(), pageMarkdown: pageMarkdown() },   // free tier, or WEBEXTRACT_API_KEY if set
  stopWhen: stepCountIs(3),
});
```

Options are the same as the `@webextract/sdk` client: `apiKey` (prepaid credits), `paymentFetch` (x402 pay per call via `@x402/fetch`; this package never sees your private key), `billing: "x402-testnet"` (sandbox), `baseUrl` and `timeoutMs`. `webextractTools(options)` returns both tools sharing one client.

By default, API errors are returned to the model as `{ ok: false, error: { error, status, message, charged, reason, hint, ... } }`, so it can react to `free_limit_reached`, `robots_disallowed` and so on. Set `onError: "throw"` to raise instead.

Works with `ai` v5–v7 (`inputSchema` tool API). It's tested with `ai` 7 + zod 4 and `ai` 5 + zod 3.

License: MIT © TAINCHENG, L.L.C.
