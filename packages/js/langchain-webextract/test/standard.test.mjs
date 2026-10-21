// Port of LangChain's Python standard tool tests (langchain-tests ToolsUnitTests + ToolsIntegrationTests).
// The JS @langchain/standard-tests package is private to the langchainjs monorepo (not on npm) and only
// covers chat models, so the same checks are reproduced here. HTTP is mocked; no network, no money.
import { test } from "node:test";
import assert from "node:assert/strict";
import { ToolMessage } from "@langchain/core/messages";
import { StructuredTool } from "@langchain/core/tools";
import { toJsonSchema } from "@langchain/core/utils/json_schema";
import { extractUrlTool, pageMarkdownTool } from "../dist/index.js";

delete process.env.WEBEXTRACT_API_KEY;
const OK = { url: "https://example.com", final_url: "https://example.com/", title: "Example Domain", markdown: "# Example", content_source: "raw_html" };
const ERR402 = { error: "payment_required", reason: "free_limit_reached", message: "Free daily limit reached" };
function mock(status, body) {
  const f = async (url, init) => { f.calls.push({ url, init }); return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...(status === 402 ? { "x-payment-reason": body.reason } : {}) } }); };
  f.calls = []; return f;
}
const EXAMPLE = { url: "https://example.com" };

for (const [label, factory] of [["extract_url", extractUrlTool], ["page_markdown", pageMarkdownTool]]) {
  for (const [variant, status, body] of [["200", 200, OK], ["402", 402, ERR402]]) {
    const make = () => factory({ fetch: mock(status, body) });
    // ---- ToolsUnitTests ----
    test(`[${label}/${variant}] test_init`, () => { assert.ok(make()); });
    test(`[${label}/${variant}] test_has_name`, () => { const t = make(); assert.ok(t instanceof StructuredTool); assert.equal(t.name, label); });
    test(`[${label}/${variant}] test_has_input_schema`, () => {
      const js = toJsonSchema(make().schema);
      assert.equal(js.type, "object"); assert.deepEqual(js.required, ["url"]); assert.equal(js.properties.url.type, "string");
    });
    test(`[${label}/${variant}] test_input_schema_matches_invoke_params`, () => { assert.ok(make().schema.safeParse(EXAMPLE).success); });
    // ---- ToolsIntegrationTests (offline) ----
    const call = { name: label, args: EXAMPLE, id: "123", type: "tool_call" };
    test(`[${label}/${variant}] test_invoke_matches_output_schema`, async () => {
      const msg = await make().invoke(call);
      assert.ok(msg instanceof ToolMessage); assert.equal(msg.tool_call_id, "123");
      assert.ok(typeof msg.content === "string" || Array.isArray(msg.content));
      JSON.parse(msg.content);
    });
    test(`[${label}/${variant}] test_invoke_no_tool_call (must not throw)`, async () => { await make().invoke(EXAMPLE); });
    test(`[${label}/${variant}] test_batch_no_tool_call (must not throw)`, async () => { const out = await make().batch([EXAMPLE, EXAMPLE]); assert.equal(out.length, 2); });
  }
  test(`[${label}] test_init_from_env: WEBEXTRACT_API_KEY becomes the Bearer key`, async () => {
    process.env.WEBEXTRACT_API_KEY = "lx_test_env_key";
    try {
      const f = mock(200, OK);
      await factory({ fetch: f }).invoke(EXAMPLE);
      assert.equal(f.calls[0].init.headers.authorization, "Bearer lx_test_env_key");
    } finally { delete process.env.WEBEXTRACT_API_KEY; }
  });
}
