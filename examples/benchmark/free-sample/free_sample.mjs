#!/usr/bin/env node
// Reproduce the WebExtract free-path sample with one command (Node 18+, no dependencies).
//
//   node free_sample.mjs        // up to 14 calls: 7 public pages x /v1/markdown and /v1/extract
//   node free_sample.mjs 4      // only the first 4 calls
//
// It uses the free path (header `X-Billing: free`): 20 calls per caller IP per day, shared with MCP.
// It stops at the first non-200 answer (HTTP 402 `free_limit_reached` means today's free calls from your IP are used up).
// No wallet, no payment. Set WEBEXTRACT_BASE to use another server, WEBEXTRACT_UA to set your own User-Agent.
const BASE = (process.env.WEBEXTRACT_BASE || "https://api.webextract.dev").replace(/\/+$/, "");
const UA = process.env.WEBEXTRACT_UA || "webextract-benchmark-example/1 (node)";
const PAGES = [
  "https://example.com/",
  "https://books.toscrape.com/",
  "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "https://quotes.toscrape.com/",
  "https://webscraper.io/test-sites/tables",
  "https://www.scrapethissite.com/pages/forms/",
  "https://httpbin.org/html",
];
const limit = Number(process.argv[2] || 14);
const calls = PAGES.flatMap((u) => ["markdown", "extract"].map((ep) => [ep, u])).slice(0, limit);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

console.log(`${"endpoint".padEnd(9)} ${"status".padEnd(6)} ${"ms".padStart(6)} ${"free left".padStart(9)} ${"words".padStart(6)}  page`);
let ok = 0;
for (const [ep, page] of calls) {
  const t0 = performance.now();
  const r = await fetch(`${BASE}/v1/${ep}?` + new URLSearchParams({ url: page }), {
    headers: { "User-Agent": UA, "X-Billing": "free" },
    signal: AbortSignal.timeout(90000),
  });
  const text = await r.text();
  const ms = Math.round(performance.now() - t0);
  let data = {};
  try { data = JSON.parse(text); } catch {}
  const left = r.headers.get("x-free-remaining") ?? "-";
  const words = r.status === 200 ? data.word_count ?? "-" : "-";
  console.log(`${ep.padEnd(9)} ${String(r.status).padEnd(6)} ${String(ms).padStart(6)} ${String(left).padStart(9)} ${String(words).padStart(6)}  ${page}`);
  if (r.status !== 200) { console.log("stopped:", r.status, data.reason || data.error || text.slice(0, 200)); break; }
  if (!String(data.markdown ?? "").trim()) { console.log("stopped: HTTP 200 but empty markdown"); break; }
  ok++;
  await sleep(3000);
}
console.log(`${ok} of ${calls.length} calls returned HTTP 200 with markdown.`);
process.exit(ok === calls.length ? 0 : 1);
