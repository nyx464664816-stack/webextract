// Pay-per-call with x402 (USDC on Base, Polygon, Arbitrum, Avalanche, OP Mainnet, World Chain or Monad). npm i @x402/fetch @x402/evm viem
// Use a low-balance hot wallet you control; never commit its key.
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY);
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
schemes: [{ network: "eip155:*", client: new ExactEvmScheme(account) }], // any EVM network the API accepts
});

const target = process.argv[2] || "https://example.com";
const res = await fetchWithPayment(
`https://api.webextract.dev/v1/markdown?url=${encodeURIComponent(target)}`,
{ headers: { "X-Billing": "x402" } } // skip the free tier and pay ($0.002)
);
console.log(res.status, res.headers.get("PAYMENT-RESPONSE") ? "(paid)" : "");
console.log(await res.json());
