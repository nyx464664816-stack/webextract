# @webextract/langchain

[LangChain.js](https://js.langchain.com) tools for [WebExtract](https://webextract.dev). The tool names and outputs match the WebExtract MCP tools:

- `extract_url`: clean Markdown plus fixed-schema JSON (metadata, product and price with `price_detail`, tables). $0.005 or 1 credit.
- `page_markdown`: clean Markdown only. $0.002 or 0.4 credit.

```bash
npm i @webextract/langchain @langchain/core zod
```

```ts
import { webextractTools, extractUrlTool } from "@webextract/langchain";

const tools = webextractTools();                       // free tier, or WEBEXTRACT_API_KEY if set
const tools2 = webextractTools({ apiKey: "lx_..." });  // prepaid credits
console.log(await extractUrlTool().invoke({ url: "https://web-scraping.dev/product/1" }));
```

For x402 pay per call, pass `paymentFetch` (e.g. `wrapFetchWithPaymentFromConfig` from `@x402/fetch`). This package never sees your private key.

The tools return a JSON string. By default, API errors come back as `{"ok":false,"error":{...}}` (including the 402 `reason` and `hint`). Set `onError: "throw"` to raise instead.

For the Python LangChain tools, see PyPI [`langchain-webextract`](https://pypi.org/project/langchain-webextract/).

License: MIT © TAINCHENG, L.L.C.
