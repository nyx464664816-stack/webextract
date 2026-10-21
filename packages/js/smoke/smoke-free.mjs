// Real call #1 (JS): free tier via X-Billing: free. No payment. If the daily quota is used up the API
// answers 402 free_limit_reached, which is itself a check of the error mapping.
import { WebExtract, PaymentRequiredError } from "../webextract/dist/index.js";
const we = new WebExtract();
const target = process.argv[2] || "https://example.com";
console.log(new Date().toISOString(), "balance:", JSON.stringify(await we.balance()));
try {
  const r = await we.markdown(target);
  console.log("HTTP", r.meta.status, "billing", r.meta.billing, "free_remaining", r.meta.freeRemaining, "content_source", r.data.content_source ?? "(absent)", "words", r.data.word_count);
} catch (e) {
  if (e instanceof PaymentRequiredError) console.log("HTTP", e.status, e.name, "reason", e.reason, "free_remaining", e.freeRemaining, "networks", e.networks.join(","), "charged", e.charged);
  else { console.log("ERROR", e.name, e.status, e.code, e.message); process.exitCode = 1; }
}
