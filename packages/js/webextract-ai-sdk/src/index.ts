import { tool, type Tool } from "ai";
import { z } from "zod";
import { WebExtract, WebExtractError, TOOL_DESCRIPTIONS, type WebExtractOptions, type ExtractResult, type MarkdownResult } from "@webextract/sdk";

export interface WebExtractToolOptions extends WebExtractOptions {
  /** Reuse an existing client instead of building one from the options. */
  client?: WebExtract;
  /** "return" (default): API errors (402 reason, failed fetch, bad url) come back to the model as
   * `{ ok: false, error: {...} }` so it can react. "throw": rethrow (AI SDK reports a tool-error). */
  onError?: "return" | "throw";
}

export type ToolError = { ok: false; error: Record<string, unknown> };
export type WebExtractInput = { url: string };
export type ExtractUrlTool = Tool<WebExtractInput, ExtractResult | ToolError>;
export type PageMarkdownTool = Tool<WebExtractInput, MarkdownResult | ToolError>;

const inputSchema: z.ZodType<WebExtractInput> = z.object({ url: z.string().url().describe(TOOL_DESCRIPTIONS.url) });

function clientFrom(opts: WebExtractToolOptions): WebExtract {
  if (opts.client) return opts.client;
  const { client: _c, onError: _o, ...rest } = opts;
  return new WebExtract(rest);
}

async function run<T>(opts: WebExtractToolOptions, fn: () => Promise<T>): Promise<T | ToolError> {
  try { return await fn(); }
  catch (e) {
    if (opts.onError !== "throw" && e instanceof WebExtractError) return { ok: false, error: e.toJSON() };
    throw e;
  }
}

/** Vercel AI SDK tool: Markdown + fixed-schema JSON (metadata, product/price, tables) for a URL. */
export function extractUrl(opts: WebExtractToolOptions = {}): ExtractUrlTool {
  const client = clientFrom(opts);
  return tool({
    description: TOOL_DESCRIPTIONS.extract_url,
    inputSchema,
    execute: async ({ url }, { abortSignal }): Promise<ExtractResult | ToolError> =>
      run(opts, async () => (await client.extract(url, { signal: abortSignal })).data),
  });
}

/** Vercel AI SDK tool: clean Markdown for a URL (cheaper). */
export function pageMarkdown(opts: WebExtractToolOptions = {}): PageMarkdownTool {
  const client = clientFrom(opts);
  return tool({
    description: TOOL_DESCRIPTIONS.page_markdown,
    inputSchema,
    execute: async ({ url }, { abortSignal }): Promise<MarkdownResult | ToolError> =>
      run(opts, async () => (await client.markdown(url, { signal: abortSignal })).data),
  });
}

/** Both tools sharing one client: `tools: webextractTools({ apiKey })`. */
export function webextractTools(opts: WebExtractToolOptions = {}): { extractUrl: ExtractUrlTool; pageMarkdown: PageMarkdownTool } {
  const client = clientFrom(opts);
  return { extractUrl: extractUrl({ ...opts, client }), pageMarkdown: pageMarkdown({ ...opts, client }) };
}

export { WebExtract } from "@webextract/sdk";
export type { WebExtractOptions } from "@webextract/sdk";
