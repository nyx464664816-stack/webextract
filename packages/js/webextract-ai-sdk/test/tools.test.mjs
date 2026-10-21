// Unit tests with mocked HTTP and a mock language model. No network, no money.
import { test } from "node:test";
import assert from "node:assert/strict";
import { generateText, stepCountIs } from "ai";
import { MockLanguageModelV4 } from "ai/test";
import { extractUrl, pageMarkdown, webextractTools, WebExtract } from "../dist/index.js";

delete process.env.WEBEXTRACT_API_KEY; // tests control the env explicitly
const MD = { url: "https://a.test/", final_url: "https://a.test/", title: "A", markdown: "# A", content_source: "raw_html" };
const EX = { url: "https://a.test/", final_url: "https://a.test/", fetched_at: "t", schema_version: "1.0", markdown: "# A", metadata: {}, product: null, product_unresolved: { reason: "listing_page" }, tables: [] };
function mock(status, body, headers = {}) {
  const f = async (url, init) => { f.calls.push({ url, init }); return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } }); };
  f.calls = []; return f;
}
const opts = { toolCallId: "t1", messages: [], abortSignal: undefined };

test("tools expose description + zod inputSchema that rejects bad urls", async () => {
  const t = extractUrl({ fetch: mock(200, EX) });
  assert.match(t.description, /Markdown/);
  assert.ok(t.inputSchema.safeParse({ url: "https://a.test/" }).success);
  assert.equal(t.inputSchema.safeParse({ url: "nope" }).success, false);
  assert.equal(t.inputSchema.safeParse({}).success, false);
});

test("extractUrl.execute returns the API JSON (incl. new optional fields)", async () => {
  const f = mock(200, EX);
  const out = await extractUrl({ fetch: f }).execute({ url: "https://a.test/" }, opts);
  assert.equal(out.product_unresolved.reason, "listing_page");
  assert.equal(new URL(f.calls[0].url).pathname, "/v1/extract");
  assert.equal(f.calls[0].init.headers["x-billing"], "free");
});

test("pageMarkdown.execute hits /v1/markdown with Bearer when apiKey is set", async () => {
  const f = mock(200, MD);
  const out = await pageMarkdown({ apiKey: "lx_k", fetch: f }).execute({ url: "https://a.test/" }, opts);
  assert.equal(out.markdown, "# A");
  assert.equal(new URL(f.calls[0].url).pathname, "/v1/markdown");
  assert.equal(f.calls[0].init.headers.authorization, "Bearer lx_k");
});

test("API errors come back to the model as { ok:false, error } by default", async () => {
  const f = mock(402, { error: "payment_required", reason: "free_limit_reached", message: "Free daily limit reached" }, { "x-payment-reason": "free_limit_reached", "x-free-remaining": "0" });
  const out = await extractUrl({ fetch: f }).execute({ url: "https://a.test/" }, opts);
  assert.equal(out.ok, false);
  assert.equal(out.error.reason, "free_limit_reached");
  assert.equal(out.error.status, 402);
  assert.equal(out.error.charged, false);
  assert.match(out.error.hint, /x402/);
});

test("onError: throw rethrows", async () => {
  const f = mock(451, { error: "robots_disallowed", message: "robots", charged: false });
  await assert.rejects(pageMarkdown({ fetch: f, onError: "throw" }).execute({ url: "https://a.test/" }, opts), e => e.name === "TargetFetchError");
});

test("webextractTools shares one client and paymentFetch", async () => {
  const pf = mock(200, MD);
  const tools = webextractTools({ paymentFetch: pf });
  assert.deepEqual(Object.keys(tools), ["extractUrl", "pageMarkdown"]);
  await tools.pageMarkdown.execute({ url: "https://a.test/" }, opts);
  assert.equal(pf.calls.length, 1);
  assert.equal(pf.calls[0].init.headers["x-billing"], undefined);
  const c = new WebExtract({ fetch: pf });
  assert.equal(webextractTools({ client: c }).extractUrl.description.length > 0, true);
});

test("end-to-end through generateText with a mock model calling pageMarkdown", async () => {
  const f = mock(200, MD);
  let step = 0;
  const model = new MockLanguageModelV4({
    doGenerate: async () => {
      step++;
      const usage = { inputTokens: { total: 1, noCache: 1, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 1, text: 1, reasoning: 0 } };
      if (step === 1) return { content: [{ type: "tool-call", toolCallId: "c1", toolName: "pageMarkdown", input: JSON.stringify({ url: "https://a.test/" }) }], finishReason: { unified: "tool-calls", raw: undefined }, usage, warnings: [] };
      return { content: [{ type: "text", text: "done" }], finishReason: { unified: "stop", raw: undefined }, usage, warnings: [] };
    },
  });
  const r = await generateText({ model, tools: webextractTools({ fetch: f }), prompt: "read https://a.test/", stopWhen: stepCountIs(3) });
  assert.equal(r.text, "done");
  const results = r.steps.flatMap(s => s.toolResults);
  assert.equal(results.length, 1);
  assert.equal(results[0].toolName, "pageMarkdown");
  assert.equal(results[0].output.markdown, "# A");
  assert.equal(f.calls.length, 1);
});
