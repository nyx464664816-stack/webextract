# Public information about other tools (copied from their own pages, read 2026-10-26 KST)

Only what the vendors state on their public pages. We did not run these tools and publish no numbers for them. "Not found" means the page we read does not say.
Their prices and limits change; check the linked pages.

Sources: Jina Reader https://jina.ai/reader/ ; Firecrawl https://www.firecrawl.dev/pricing and https://docs.firecrawl.dev/introduction (all read 2026-10-26 KST).

| | WebExtract | Jina Reader | Firecrawl |
|---|---|---|---|
| Account or API key needed to start | No (free opt-in, or pay per call) | Rate-limit table, Reader API row: 20 RPM "w/o API Key", 500 RPM "w/ Free API Key", 500 RPM "w/ Paid API Key", 5000 RPM "w/ Premium API Key" | Docs, "Get started": "No account or API key is required for this request." and "Add an API key when you need higher limits." |
| Markdown output | yes (`/v1/markdown`) | yes (`r.jina.ai/<url>`) | yes (`formats: ["markdown"]`) |
| Structured JSON | fixed schema in `/v1/extract`: `product`, `tables`, `metadata` | FAQ: "Use the x-json-schema header with a JSON schema definition, or use x-instruction header with natural language instructions. Both features work with ReaderLM-v2" | "structured JSON" format (their docs); pricing page: "the JSON, Question, and Highlight formats add 4 credits per page" |
| How it is priced | per call: $0.002 markdown, $0.005 extract (x402 quote, `results/quotes.json`); prepaid credits also exist | tokens: the Reader API row says "Count the number of tokens in the output response"; the token price is not on the page we read | credits: 1 credit per scraped page; plans from Free (1,000 credits per month, "no card") to Scale; pricing page: "we add credits in 5 USD increments" on paid plans |
| Payment methods | USDC through x402 on 7 networks; card (Stripe) for prepaid credits | FAQ: "Payments are processed through Stripe, supporting a variety of payment methods including credit cards, Google Pay, and PayPal"; x402: not found | FAQ: Stripe (cards, PayPal); sold on AWS Marketplace and Google Cloud Marketplace; x402: not found |
| Failed requests | Sandbox: not charged, measured in `results/failures.json`. Live `/v1`: not measured on the paid path, docs state no charge | FAQ: "No, tokens are not deducted for failed requests." | FAQ: "A scrape that returns no result is not charged. A page that responds with an error status such as 403 or 404 is still returned to you and costs 1 credit." |
| Free allowance | 20 calls per caller IP per day, REST and MCP share one counter (REST needs the opt-in header; details in the docs) | FAQ: new users get an auto-generated API key with free tokens; without a key the limit above is 20 RPM (a rate limit, not a quota) | Free plan: 1,000 credits per month |

Quoted sentences are copied word for word.
