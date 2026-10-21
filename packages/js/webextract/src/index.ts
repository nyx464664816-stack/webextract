export { WebExtract, VERSION, DEFAULT_BASE_URL, ENV_API_KEY, toError } from "./client.js";
export type { WebExtractOptions, RequestOptions } from "./client.js";
export * from "./errors.js";
export type * from "./types.js";

/** Tool descriptions shared by the AI SDK and LangChain wrappers (kept in sync with the MCP tools). */
export const TOOL_DESCRIPTIONS = {
  extract_url: "Fetch a public web page (robots.txt respected) and return clean Markdown plus fixed-schema JSON: article metadata, product/price (with price_detail when available; a missing price is never reported as 0), and tables. Paid per call (USDC on Base and 6 other chains via x402, or prepaid credits); free tier 50 calls/day per IP.",
  page_markdown: "Fetch a public web page (robots.txt respected) and return clean Markdown only. Cheaper than extract_url. Use it when you only need the text.",
  url: "Public http(s) URL of the page to read",
} as const;
