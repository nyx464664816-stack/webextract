// Unit tests with mocked HTTP. No network, no money.
import { test } from "node:test";
import assert from "node:assert/strict";
import { extractUrlTool, pageMarkdownTool, webextractTools } from "../dist/index.js";

delete process.env.WEBEXTRACT_API_KEY; // tests control the env explicitly
const MD = { url: "https://a.test/", final_url: "https://a.test/", title: "A", markdown: "# A" };
const EX = { url: "https://a.test/", final_url: "https://a.test/", fetched_at: "t", schema_version: "1.0", markdown: "# A", metadata: {}, product: { name: "P", price: 19.99, currency: "USD", price_detail: { status: "resolved", prices: [{ type: "sale", amount: 19.99, currency: "USD" }] } }, tables: [] };
function mock(status, body, headers = {}) {
  const f = async (url, init) => { f.calls.push({ url, init }); return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } }); };
  f.calls = []; return f;
}

test("tool names match the MCP tools", () => {
  const [a, b] = webextractTools({ fetch: mock(200, MD) });
  assert.equal(a.name, "extract_url"); assert.equal(b.name, "page_markdown");
  assert.match(a.description, /Markdown/);
});

test("extract_url.invoke returns JSON string of the API result", async () => {
  const f = mock(200, EX);
  const out = await extractUrlTool({ fetch: f }).invoke({ url: "https://a.test/" });
  const j = JSON.parse(out);
  assert.equal(j.product.price_detail.prices[0].type, "sale");
  assert.equal(new URL(f.calls[0].url).pathname, "/v1/extract");
});

test("page_markdown with apiKey uses Bearer", async () => {
  const f = mock(200, MD);
  const out = JSON.parse(await pageMarkdownTool({ apiKey: "lx_k", fetch: f }).invoke({ url: "https://a.test/" }));
  assert.equal(out.markdown, "# A");
  assert.equal(f.calls[0].init.headers.authorization, "Bearer lx_k");
});

test("schema rejects invalid url before any HTTP call", async () => {
  const f = mock(200, MD);
  await assert.rejects(pageMarkdownTool({ fetch: f }).invoke({ url: "nope" }));
  assert.equal(f.calls.length, 0);
});

test("402 reason is returned as JSON error string by default", async () => {
  const f = mock(402, { error: "payment_required", reason: "x402_required", message: "Payment required" }, { "x-payment-reason": "x402_required" });
  const out = JSON.parse(await extractUrlTool({ fetch: f }).invoke({ url: "https://a.test/" }));
  assert.equal(out.ok, false); assert.equal(out.error.reason, "x402_required"); assert.equal(out.error.charged, false);
});

test("onError: throw rethrows TargetFetchError", async () => {
  const f = mock(422, { error: "upstream_error", message: "HTTP 404; not charged", charged: false });
  await assert.rejects(extractUrlTool({ fetch: f, onError: "throw" }).invoke({ url: "https://a.test/" }), e => e.name === "TargetFetchError" && e.charged === false);
});
