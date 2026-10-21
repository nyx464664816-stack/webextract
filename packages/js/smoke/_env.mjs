// Reads ONLY the testnet key from examples/python-x402/.env (mode 600). Never prints it.
import { readFileSync, statSync } from "node:fs";
export const ENV_PATH = new URL("../../../examples/python-x402/.env", import.meta.url).pathname;
export function testnetKey() {
  if ((statSync(ENV_PATH).mode & 0o077) !== 0) throw new Error(`${ENV_PATH} must be mode 600`);
  const line = readFileSync(ENV_PATH, "utf8").split("\n").find(l => l.startsWith("X402_TESTNET_PRIVATE_KEY="));
  const k = line?.slice("X402_TESTNET_PRIVATE_KEY=".length).trim();
  if (!k) throw new Error("X402_TESTNET_PRIVATE_KEY missing");
  return k;
}
