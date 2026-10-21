#!/usr/bin/env bash
# Lists every file in every built artifact and fails on secrets / env files / HTML fixtures / test wallets.
set -euo pipefail
cd "$(dirname "$0")/dist-local"
KEY=$(grep -h '^X402_TESTNET_PRIVATE_KEY=' ../../examples/python-x402/.env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || true)
fail=0; tmp=$(mktemp -d)
for a in *.tgz py/*.tar.gz py/*.whl; do
  d="$tmp/$(basename "$a")"; mkdir -p "$d"
  case "$a" in *.whl) python3 -m zipfile -e "$a" "$d" ;; *) tar -xzf "$a" -C "$d" ;; esac
  n=$(find "$d" -type f | wc -l); echo "== $a ($n files)"; (cd "$d" && find . -type f | sort | sed 's/^/   /')
  bad=$(cd "$d" && find . -type f \( -name '.env*' -o -name '*.html' -o -name '*.htm' -o -name '*.pem' -o -name '*.key' -o -name 'node_modules' -o -path '*/fixtures/*' -o -name '*.pyc' \) | sort || true)
  [ -n "$bad" ] && { echo "   !! forbidden files: $bad"; fail=1; }
  if grep -rIlE '(PRIVATE_KEY=0x|-----BEGIN|lx_[A-Za-z0-9]{16,}|sk_live_|rk_live_)' "$d" >/dev/null 2>&1; then echo "   !! secret-like pattern:"; grep -rIlE '(PRIVATE_KEY=0x|-----BEGIN|lx_[A-Za-z0-9]{16,}|sk_live_|rk_live_)' "$d"; fail=1; fi
  if grep -rIoE '0x[0-9a-fA-F]{64}' "$d" >/dev/null 2>&1; then echo "   !! 32-byte hex found (possible key):"; grep -rIoE '0x[0-9a-fA-F]{64}' "$d" | head; fail=1; fi
  if [ -n "$KEY" ] && grep -rIqF "${KEY#0x}" "$d"; then echo "   !! TESTNET KEY FOUND"; fail=1; fi
done
rm -rf "$tmp"; [ $fail = 0 ] && echo "CLEAN: no .env, keys, secrets, HTML or fixtures in any artifact" || { echo "FAILED"; exit 1; }
