// Pay per call with x402 on whichever supported network your wallet actually holds USDC on.
//   cd examples/node && npm i
//   EVM_PRIVATE_KEY=0x... node x402-fetch.mjs https://example.com          # pays $0.002 for /v1/markdown
//   WALLET_ADDRESS=0x... node x402-fetch.mjs --dry-run https://example.com  # only shows balances + chosen network, signs nothing
//   WEBEXTRACT_SANDBOX=1 EVM_PRIVATE_KEY=0x... node x402-fetch.mjs          # sandbox: Base Sepolia test USDC only, free test money
// Use a low-balance hot wallet you control; never commit its key.
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const BASE = process.env.WEBEXTRACT_BASE || "https://api.webextract.dev";
const SANDBOX = process.env.WEBEXTRACT_SANDBOX === "1";
const args = process.argv.slice(2);
const DRY = args.includes("--dry-run");
const target = args.find(a => !a.startsWith("--")) || "https://example.com";
const ENDPOINT = `${BASE}${SANDBOX ? "/sandbox" : ""}/v1/markdown?url=${encodeURIComponent(target)}`;

// network -> [USDC address, public RPC]. Base first = preferred when several have enough balance.
const USDC = SANDBOX ? { "eip155:84532": ["0x036CbD53842c5426634e7929541eC2318f3dCF7e", "https://sepolia.base.org"] } : {
  "eip155:8453": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "https://mainnet.base.org"],
  "eip155:137": ["0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "https://polygon-rpc.com"],
  "eip155:42161": ["0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "https://arb1.arbitrum.io/rpc"],
  "eip155:480": ["0x79A02482A880bCE3F13e09Da970dC34db4CD24d1", "https://worldchain-mainnet.g.alchemy.com/public"],
  "eip155:143": ["0x754704Bc059F8C67012fEd69BC8A327a5aafb603", "https://rpc1.monad.xyz"],
  "eip155:43114": ["0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "https://api.avax.network/ext/bc/C/rpc"],
  "eip155:10": ["0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "https://mainnet.optimism.io"],
};
// @x402/evm 2.28 (and Python x402 2.25) have no default asset for OP Mainnet / World Chain:
// without these allowedAssets entries the SDK's spendControls reject those options.
const MAX_ATOMIC = "10000"; // $0.01 cap per payment (USDC has 6 decimals)
const allowedAssets = Object.entries(USDC).map(([network, [asset]]) => ({ network, asset, maxAmountPerPayment: MAX_ATOMIC }));

async function usdcBalance(network, owner) {
  const [asset, rpc] = USDC[network];
  const data = "0x70a08231" + owner.toLowerCase().replace(/^0x/, "").padStart(64, "0"); // balanceOf(owner)
  try {
    const r = await fetch(rpc, { method: "POST", headers: { "content-type": "application/json" }, signal: AbortSignal.timeout(8000),
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: asset, data }, "latest"] }) });
    const j = await r.json();
    return j.result && j.result !== "0x" ? BigInt(j.result) : 0n;
  } catch { return null; } // RPC unreachable: treat as unknown
}

const account = process.env.EVM_PRIVATE_KEY ? privateKeyToAccount(process.env.EVM_PRIVATE_KEY) : null;
const owner = account?.address || process.env.WALLET_ADDRESS;
if (!owner) { console.error("set EVM_PRIVATE_KEY (to pay) or WALLET_ADDRESS (with --dry-run)"); process.exit(1); }

const balances = Object.fromEntries(await Promise.all(Object.keys(USDC).map(async n => [n, await usdcBalance(n, owner)])));
for (const [n, b] of Object.entries(balances)) console.log(`${n.padEnd(13)} USDC ${b === null ? "rpc error" : (Number(b) / 1e6).toFixed(6)}`);

// Pick among the options the server offers: the first (Base preferred) network where this wallet has enough USDC.
const selector = (_version, reqs) => {
  const ok = reqs.filter(r => balances[r.network] != null && balances[r.network] >= BigInt(r.amount));
  if (!ok.length) throw new Error(`no supported network with enough USDC for ${owner}; offered: ${reqs.map(r => r.network).join(", ")}`);
  return ok[0];
};
const funded = Object.keys(USDC).filter(n => balances[n] > 0n);
if (DRY) {
  const res = await fetch(ENDPOINT, { headers: { "X-Billing": SANDBOX ? "x402-testnet" : "x402" } });
  const { decodePaymentRequiredHeader } = await import("@x402/core/http");
  const pr = decodePaymentRequiredHeader(res.headers.get("payment-required"));
  try { const r = selector(pr.x402Version, pr.accepts); console.log(`would pay ${r.amount} atomic USDC on ${r.network} (dry run, nothing signed)`); }
  catch (e) { console.log(e.message); }
  process.exit(0);
}
if (!account) { console.error("EVM_PRIVATE_KEY is required to pay"); process.exit(1); }
if (!funded.length) { console.error("this wallet has no USDC on any supported network"); process.exit(1); }

const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: funded.map(network => ({ network, client: new ExactEvmScheme(account) })), // only networks with a balance
  paymentRequirementsSelector: selector,
  spendControls: { allowedAssets },
});
const res = await fetchWithPayment(ENDPOINT, { headers: { "X-Billing": SANDBOX ? "x402-testnet" : "x402" } }); // optional for mainnet (a bare request already gets the 402); required for the sandbox
console.log(res.status, res.headers.get("PAYMENT-RESPONSE") ? "(paid)" : "");
const body = await res.json();
console.log(res.status === 402 ? `${body.reason}: ${body.message}` : body);
