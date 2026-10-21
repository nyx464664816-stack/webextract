// Unit tests: all HTTP is mocked. No network, no money.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  WebExtract, WebExtractError, PaymentRequiredError, TargetFetchError, InvalidRequestError,
  AuthenticationError, RateLimitError, ConnectionError,
} from "../dist/index.js";

delete process.env.WEBEXTRACT_API_KEY; // tests control the env explicitly
const b64 = o => Buffer.from(JSON.stringify(o)).toString("base64");
const PR = { x402Version: 2, accepts: [{ network: "eip155:8453" }, { network: "eip155:137" }, { network: "eip155:8453" }] };
const EXTRACT = {
  url: "https://shop.test/p/1?variant=red", final_url: "https://shop.test/p/1?variant=red", fetched_at: "2026-10-21T11:00:00.000Z",
  schema_version: "1.0", markdown: "# P", metadata: { title: "P" }, tables: [], content_source: "raw_html",
  product: { name: "P", price: null, currency: "USD", source: "json-ld",
    price_detail: { status: "unresolved", prices: [], unresolved: { reason: "variant_not_matched", detail: "x" }, warnings: ["flat_price_withheld_variant_not_matched"] } },
};
function mock(status, body, headers = {}) {
  const calls = [];
  const f = async (url, init) => {
    calls.push({ url, init });
    const text = typeof body === "string" ? body : JSON.stringify(body);
    return new Response(text, { status, headers: { "content-type": "application/json", ...headers } });
  };
  f.calls = calls;
  return f;
}
const hdr = (call, k) => call.init.headers[k.toLowerCase()];

test("default billing is free: GET /v1/extract with X-Billing: free, url encoded, no auth", async () => {
  const f = mock(200, EXTRACT, { "x-free-remaining": "41" });
  const r = await new WebExtract({ fetch: f }).extract("https://shop.test/p/1?variant=red&a=b");
  assert.equal(f.calls.length, 1);
  const u = new URL(f.calls[0].url);
  assert.equal(u.origin + u.pathname, "https://api.webextract.dev/v1/extract");
  assert.equal(u.searchParams.get("url"), "https://shop.test/p/1?variant=red&a=b");
  assert.equal(f.calls[0].init.method, "GET");
  assert.equal(hdr(f.calls[0], "x-billing"), "free");
  assert.equal(hdr(f.calls[0], "authorization"), undefined);
  assert.equal(r.meta.billing, "free");
  assert.equal(r.meta.freeRemaining, 41);
});

test("new optional fields pass through untouched", async () => {
  const r = await new WebExtract({ fetch: mock(200, EXTRACT) }).extract("https://shop.test/p/1");
  assert.equal(r.data.content_source, "raw_html");
  assert.equal(r.data.product.price, null);
  assert.equal(r.data.product.price_detail.unresolved.reason, "variant_not_matched");
});

test("apiKey: Bearer header, no X-Billing, credit headers parsed", async () => {
  const f = mock(200, EXTRACT, { "x-credits-charged": "0.4", "x-credits-remaining": "999.6" });
  const r = await new WebExtract({ apiKey: "lx_secret", fetch: f }).extract("https://a.test/");
  assert.equal(hdr(f.calls[0], "authorization"), "Bearer lx_secret");
  assert.equal(hdr(f.calls[0], "x-billing"), undefined);
  assert.equal(r.meta.billing, "key");
  assert.equal(r.meta.creditsCharged, 0.4);
  assert.equal(r.meta.creditsRemaining, 999.6);
});

test("paymentFetch: used for the call, no X-Billing header, PAYMENT-RESPONSE decoded", async () => {
  const pf = mock(200, { url: "u", final_url: "u", title: null, markdown: "hi" }, { "payment-response": b64({ success: true, transaction: "0xabc", network: "eip155:8453" }) });
  const plain = mock(500, {});
  const r = await new WebExtract({ paymentFetch: pf, fetch: plain }).markdown("https://a.test/");
  assert.equal(pf.calls.length, 1); assert.equal(plain.calls.length, 0);
  assert.equal(new URL(pf.calls[0].url).pathname, "/v1/markdown");
  assert.equal(hdr(pf.calls[0], "x-billing"), undefined);
  assert.equal(r.meta.billing, "x402");
  assert.equal(r.meta.paymentResponse.transaction, "0xabc");
});

test("x402-testnet billing sends X-Billing: x402-testnet and reads X-Sandbox", async () => {
  const pf = mock(200, { url: "u", final_url: "u", title: null, markdown: "hi" }, { "x-sandbox": "true" });
  const r = await new WebExtract({ paymentFetch: pf, billing: "x402-testnet" }).markdown("https://a.test/");
  assert.equal(hdr(pf.calls[0], "x-billing"), "x402-testnet");
  assert.equal(r.meta.sandbox, true);
});

test("free-first with paymentFetch when billing: free is explicit", async () => {
  const pf = mock(200, EXTRACT);
  await new WebExtract({ paymentFetch: pf, billing: "free" }).extract("https://a.test/");
  assert.equal(hdr(pf.calls[0], "x-billing"), "free");
});

test("baseUrl override and trailing slash", async () => {
  const f = mock(200, EXTRACT);
  await new WebExtract({ fetch: f, baseUrl: "http://localhost:8787/" }).extract("https://a.test/");
  assert.ok(f.calls[0].url.startsWith("http://localhost:8787/v1/extract?"));
});

test("constructor rejects ambiguous billing configs", () => {
  assert.throws(() => new WebExtract({ apiKey: "k", paymentFetch: mock(200, {}) }), /not both/);
  assert.throws(() => new WebExtract({ billing: "x402" }), /needs paymentFetch/);
  assert.throws(() => new WebExtract({ billing: "x402-testnet" }), /needs paymentFetch/);
  assert.throws(() => new WebExtract({ billing: "key" }), /needs apiKey/);
  assert.throws(() => new WebExtract({ apiKey: "k", billing: "free" }), /cannot be combined/);
  assert.throws(() => new WebExtract({ apiKey: " " }), /non-empty/);
});

test("custom headers cannot override auth or billing headers", async () => {
  const f = mock(200, EXTRACT);
  await new WebExtract({ fetch: f, headers: { "X-Billing": "x402", Authorization: "Bearer evil", "PAYMENT-SIGNATURE": "z", "x-trace": "1" } }).extract("https://a.test/");
  const h = f.calls[0].init.headers;
  assert.equal(h["x-billing"], "free"); assert.equal(h.authorization, undefined);
  assert.equal(h["PAYMENT-SIGNATURE"], undefined); assert.equal(h["X-Billing"], undefined);
  assert.equal(h["x-trace"], "1");
});

test("client-side url validation: no request is sent", async () => {
  const f = mock(200, EXTRACT);
  const c = new WebExtract({ fetch: f });
  await assert.rejects(c.extract(""), e => e instanceof InvalidRequestError && e.code === "missing_url");
  await assert.rejects(c.extract("not a url"), e => e instanceof InvalidRequestError && e.code === "invalid_url");
  await assert.rejects(c.extract("ftp://x.test/"), e => e instanceof InvalidRequestError && e.code === "invalid_url");
  assert.equal(f.calls.length, 0);
});

for (const reason of ["x402_required", "x402_requested", "free_limit_reached", "invalid_payment", "unsupported_network", "settlement_failed"]) {
  test(`402 ${reason} -> PaymentRequiredError with reason, networks, hint, charged=false`, async () => {
    const body = { error: "payment_required", reason, message: `msg ${reason}`, x402: { networks: ["eip155:8453"] }, stripe: { buy_url: "https://webextract.dev/#pricing" } };
    const headers = { "x-payment-reason": reason, "payment-required": b64(PR), ...(reason === "free_limit_reached" ? { "x-free-remaining": "0" } : {}) };
    await assert.rejects(new WebExtract({ fetch: mock(402, body, headers) }).extract("https://a.test/"), e => {
      assert.ok(e instanceof PaymentRequiredError); assert.ok(e instanceof WebExtractError);
      assert.equal(e.status, 402); assert.equal(e.reason, reason); assert.equal(e.code, "payment_required");
      assert.equal(e.message, `msg ${reason}`); assert.equal(e.charged, false);
      assert.deepEqual(e.networks, ["eip155:8453", "eip155:137"]);
      assert.equal(e.paymentRequired.x402Version, 2);
      assert.equal(e.buyUrl, "https://webextract.dev/#pricing");
      assert.equal(e.retryable, reason === "settlement_failed");
      assert.ok(e.hint.length > 10);
      if (reason === "free_limit_reached") assert.equal(e.freeRemaining, 0);
      assert.equal(e.toJSON().reason, reason);
      return true;
    });
  });
}

test("402 reason from body when header missing; networks from body when no PAYMENT-REQUIRED", async () => {
  const body = { error: "payment_required", reason: "x402_required", message: "m", x402: { networks: ["eip155:8453", "eip155:10"] } };
  await assert.rejects(new WebExtract({ fetch: mock(402, body) }).extract("https://a.test/"),
    e => e.reason === "x402_required" && e.networks.length === 2 && e.paymentRequired === null);
});

test("402 no_credits (Bearer key out of credits)", async () => {
  await assert.rejects(new WebExtract({ apiKey: "k", fetch: mock(402, { error: "no_credits", message: "Out of credits", buy: "https://webextract.dev/#pricing" }) }).extract("https://a.test/"),
    e => e instanceof PaymentRequiredError && e.reason === "no_credits" && e.code === "no_credits" && e.buyUrl === "https://webextract.dev/#pricing");
});

for (const [status, code, retryable] of [[422, "upstream_error", false], [422, "blocked_by_site", false], [451, "robots_disallowed", false], [422, "dns_failed", false], [502, "fetch_failed", true], [413, "too_large", false], [415, "unsupported_type", false]]) {
  test(`${status} ${code} -> TargetFetchError, charged=false`, async () => {
    await assert.rejects(new WebExtract({ fetch: mock(status, { error: code, message: "m; not charged", charged: false }) }).extract("https://a.test/"), e => {
      assert.ok(e instanceof TargetFetchError); assert.equal(e.code, code); assert.equal(e.status, status);
      assert.equal(e.charged, false); assert.equal(e.retryable, retryable); return true;
    });
  });
}

test("400 / 401 / 429 / 500 mapping", async () => {
  await assert.rejects(new WebExtract({ fetch: mock(400, { error: "forbidden_host", message: "private", charged: false }) }).extract("https://a.test/"), e => e instanceof InvalidRequestError && e.code === "forbidden_host");
  await assert.rejects(new WebExtract({ apiKey: "lx_secret", fetch: mock(401, { error: "invalid_api_key" }) }).extract("https://a.test/"), e => e instanceof AuthenticationError && !JSON.stringify(e.toJSON()).includes("lx_secret") && !e.message.includes("lx_secret"));
  await assert.rejects(new WebExtract({ fetch: mock(429, { error: "rate_limited", message: "Sandbox limit" }, { "retry-after": "30" }) }).extract("https://a.test/"), e => e instanceof RateLimitError && e.retryAfter === 30 && e.retryable);
  await assert.rejects(new WebExtract({ fetch: mock(500, "<html>oops</html>", { "content-type": "text/html" }) }).extract("https://a.test/"), e => e instanceof WebExtractError && e.code === "http_500" && e.retryable);
});

test("non-JSON 200 -> invalid_response", async () => {
  await assert.rejects(new WebExtract({ fetch: mock(200, "<html>", { "content-type": "text/html" }) }).extract("https://a.test/"), e => e.code === "invalid_response");
});

test("network failure and payment-wrapper exceptions -> ConnectionError with cause", async () => {
  const boom = async () => { throw new Error("No network/scheme registered for x402 version: 2"); };
  await assert.rejects(new WebExtract({ paymentFetch: boom }).extract("https://a.test/"), e => e instanceof ConnectionError && e.code === "connection_error" && /x402/.test(e.message) && !!e.cause);
});

test("timeout -> ConnectionError code timeout", async () => {
  // keep the event loop alive like a real socket would (AbortSignal.timeout timers are unref'd)
  const slow = (_u, init) => new Promise((_r, rej) => { const keep = setTimeout(() => {}, 5000); init.signal.addEventListener("abort", () => { clearTimeout(keep); rej(init.signal.reason); }); });
  await assert.rejects(new WebExtract({ fetch: slow, timeoutMs: 30 }).extract("https://a.test/"), e => e instanceof ConnectionError && e.code === "timeout");
});

test("caller abort signal is honoured", async () => {
  // keep the event loop alive like a real socket would (AbortSignal.timeout timers are unref'd)
  const slow = (_u, init) => new Promise((_r, rej) => { const keep = setTimeout(() => {}, 5000); init.signal.addEventListener("abort", () => { clearTimeout(keep); rej(init.signal.reason); }); });
  const ac = new AbortController(); setTimeout(() => ac.abort(), 10);
  await assert.rejects(new WebExtract({ fetch: slow }).extract("https://a.test/", { signal: ac.signal }), e => e instanceof ConnectionError && e.code === "connection_error");
});

test("balance(): GET /v1/balance without X-Billing", async () => {
  const f = mock(200, { plan: "free", free_remaining_today: 7 });
  const b = await new WebExtract({ fetch: f }).balance();
  assert.equal(b.free_remaining_today, 7);
  assert.equal(new URL(f.calls[0].url).pathname, "/v1/balance");
  assert.equal(hdr(f.calls[0], "x-billing"), undefined);
});

// ---- WEBEXTRACT_API_KEY fallback ----
const withEnv = async (value, fn) => {
  const old = process.env.WEBEXTRACT_API_KEY;
  if (value === undefined) delete process.env.WEBEXTRACT_API_KEY; else process.env.WEBEXTRACT_API_KEY = value;
  try { return await fn(); } finally { if (old === undefined) delete process.env.WEBEXTRACT_API_KEY; else process.env.WEBEXTRACT_API_KEY = old; }
};

test("env WEBEXTRACT_API_KEY is used when no apiKey is passed", () => withEnv(" lx_env ", async () => {
  const f = mock(200, EXTRACT);
  const c = new WebExtract({ fetch: f });
  await c.extract("https://a.test/");
  assert.equal(c.billing, "key");
  assert.equal(hdr(f.calls[0], "authorization"), "Bearer lx_env");
  assert.equal(hdr(f.calls[0], "x-billing"), undefined);
  const f2 = mock(200, EXTRACT); await new WebExtract({ fetch: f2, billing: "key" }).extract("https://a.test/");
  assert.equal(hdr(f2.calls[0], "authorization"), "Bearer lx_env");
  assert.ok(!JSON.stringify(c).includes("lx_env"));
}));

test("explicit apiKey beats env", () => withEnv("lx_env", async () => {
  const f = mock(200, EXTRACT);
  await new WebExtract({ apiKey: "lx_explicit", fetch: f }).extract("https://a.test/");
  assert.equal(hdr(f.calls[0], "authorization"), "Bearer lx_explicit");
}));

test("env is ignored with paymentFetch or a non-key billing (no mutual-exclusion error)", () => withEnv("lx_env", async () => {
  const pf = mock(200, EXTRACT);
  const c = new WebExtract({ paymentFetch: pf });
  await c.extract("https://a.test/");
  assert.equal(c.billing, "x402"); assert.equal(hdr(pf.calls[0], "authorization"), undefined);
  const f = mock(200, EXTRACT);
  const free = new WebExtract({ fetch: f, billing: "free" }); await free.extract("https://a.test/");
  assert.equal(free.billing, "free"); assert.equal(hdr(f.calls[0], "authorization"), undefined); assert.equal(hdr(f.calls[0], "x-billing"), "free");
  const pf2 = mock(200, EXTRACT);
  const tn = new WebExtract({ paymentFetch: pf2, billing: "x402-testnet" }); await tn.extract("https://a.test/");
  assert.equal(hdr(pf2.calls[0], "authorization"), undefined); assert.equal(hdr(pf2.calls[0], "x-billing"), "x402-testnet");
}));

test("blank env is ignored; billing key without any key explains the env var", () => withEnv("  ", async () => {
  assert.equal(new WebExtract({ fetch: mock(200, EXTRACT) }).billing, "free");
  assert.throws(() => new WebExtract({ billing: "key" }), /WEBEXTRACT_API_KEY/);
}));

// ---- settlement_failed auto-retry ----
function seq(...responses) {
  const f = async (url, init) => { f.calls.push({ url, init }); const [s, b, h] = responses.shift(); return new Response(JSON.stringify(b), { status: s, headers: { "content-type": "application/json", ...(h || {}) } }); };
  f.calls = []; return f;
}
const SF = [402, { error: "payment_required", reason: "settlement_failed", message: "not settled" }, { "x-payment-reason": "settlement_failed" }];

test("settlement_failed is retried once by default", async () => {
  const pf = seq(SF, [200, EXTRACT]);
  const r = await new WebExtract({ paymentFetch: pf }).extract("https://a.test/");
  assert.equal(r.meta.status, 200); assert.equal(pf.calls.length, 2);
});

test("settlement retry limit, opt-out, and validation", async () => {
  const pf = seq(SF, SF);
  await assert.rejects(new WebExtract({ paymentFetch: pf }).extract("https://a.test/"), e => e.reason === "settlement_failed");
  assert.equal(pf.calls.length, 2);
  const pf0 = seq(SF);
  await assert.rejects(new WebExtract({ paymentFetch: pf0, settlementRetries: 0 }).extract("https://a.test/"));
  assert.equal(pf0.calls.length, 1);
  assert.throws(() => new WebExtract({ settlementRetries: -1 }), /settlementRetries/);
});

test("other 402 reasons are never retried", async () => {
  const pf = seq([402, { reason: "invalid_payment" }, { "x-payment-reason": "invalid_payment" }]);
  await assert.rejects(new WebExtract({ paymentFetch: pf, settlementRetries: 5 }).extract("https://a.test/"), e => e.reason === "invalid_payment");
  assert.equal(pf.calls.length, 1);
});
