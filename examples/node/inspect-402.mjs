// Step 1 (no wallet, no payment): fetch WebExtract's 402 and decode it with the official @x402/core helper.
import { decodePaymentRequiredHeader } from "@x402/core/http";
const BASE = process.env.WEBEXTRACT_BASE || "https://api.webextract.dev";
const [endpoint = "extract", target = "https://example.com"] = process.argv.slice(2);
// Without a key, payment or X-Billing: free the server answers 402 with PAYMENT-REQUIRED; X-Billing: x402 makes it explicit.
const res = await fetch(`${BASE}/v1/${endpoint}?url=${encodeURIComponent(target)}`, { headers: { "X-Billing": "x402" } });
console.log("HTTP", res.status);
if (res.status !== 402) { console.log(await res.text()); process.exit(1); }
const pr = decodePaymentRequiredHeader(res.headers.get("payment-required"));
console.log(`x402Version=${pr.x402Version} resource=${pr.resource.url}`);
for (const a of pr.accepts) console.log(`  ${a.scheme} ${a.network.padEnd(13)} amount=${a.amount} ($${Number(a.amount) / 1e6}) asset=${a.asset} payTo=${a.payTo} extra=${JSON.stringify(a.extra)}`);
const body = await res.json();
console.log("reason:", body.reason, "| message:", body.message); // x402_required | x402_requested | free_limit_reached | invalid_payment | unsupported_network | settlement_failed
