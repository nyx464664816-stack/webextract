// Real call #2 (JS): x402 SANDBOX payment with Base Sepolia TEST USDC through @x402/fetch.
// Only eip155:84532 is registered, so the SDK cannot sign anything for a mainnet requirement.
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { WebExtract, WebExtractError } from "../webextract/dist/index.js";
import { testnetKey } from "./_env.mjs";

const NET = "eip155:84532";
const account = privateKeyToAccount(testnetKey());
console.log(new Date().toISOString(), "payer", account.address, "network", NET);
const paymentFetch = wrapFetchWithPaymentFromConfig(fetch, { schemes: [{ network: NET, client: new ExactEvmScheme(account) }] });
const we = new WebExtract({ paymentFetch, billing: "x402-testnet" });
try {
  const r = await we.markdown(process.argv[2] || "https://example.com");
  console.log("HTTP", r.meta.status, "sandbox", r.meta.sandbox, "billing", r.meta.billing);
  console.log("settlement", JSON.stringify(r.meta.paymentResponse));
  console.log("title", r.data.title, "| words", r.data.word_count, "| content_source", r.data.content_source ?? "(absent)");
} catch (e) {
  console.log("ERROR", e instanceof WebExtractError ? `${e.name} ${e.status} ${e.code} ${e.reason ?? ""} ${e.message}` : String(e));
  process.exitCode = 1;
}
