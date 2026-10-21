import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { WebExtract, WebExtractError, TOOL_DESCRIPTIONS, type WebExtractOptions } from "@webextract/sdk";

export interface WebExtractToolOptions extends WebExtractOptions {
  client?: WebExtract;
  /** "return" (default): API errors come back as a JSON string `{"ok":false,"error":{...}}`. "throw": rethrow. */
  onError?: "return" | "throw";
}

const schema = z.object({ url: z.string().url().describe(TOOL_DESCRIPTIONS.url) });

function clientFrom(opts: WebExtractToolOptions): WebExtract {
  if (opts.client) return opts.client;
  const { client: _c, onError: _o, ...rest } = opts;
  return new WebExtract(rest);
}

async function run(opts: WebExtractToolOptions, fn: () => Promise<unknown>): Promise<string> {
  try { return JSON.stringify(await fn()); }
  catch (e) {
    if (opts.onError !== "throw" && e instanceof WebExtractError) return JSON.stringify({ ok: false, error: e.toJSON() });
    throw e;
  }
}

/** LangChain.js tool `extract_url` (same name and output as the MCP tool). Returns a JSON string. */
export function extractUrlTool(opts: WebExtractToolOptions = {}) {
  const client = clientFrom(opts);
  return tool(async ({ url }, config) => run(opts, async () => (await client.extract(url, { signal: config?.signal })).data),
    { name: "extract_url", description: TOOL_DESCRIPTIONS.extract_url, schema });
}

/** LangChain.js tool `page_markdown`. Returns a JSON string. */
export function pageMarkdownTool(opts: WebExtractToolOptions = {}) {
  const client = clientFrom(opts);
  return tool(async ({ url }, config) => run(opts, async () => (await client.markdown(url, { signal: config?.signal })).data),
    { name: "page_markdown", description: TOOL_DESCRIPTIONS.page_markdown, schema });
}

/** Both tools sharing one client. */
export function webextractTools(opts: WebExtractToolOptions = {}) {
  const client = clientFrom(opts);
  return [extractUrlTool({ ...opts, client }), pageMarkdownTool({ ...opts, client })];
}

export { WebExtract } from "@webextract/sdk";
export type { WebExtractOptions } from "@webextract/sdk";
