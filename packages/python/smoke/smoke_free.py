"""Real call (Python): free tier via X-Billing: free. No payment."""
import datetime
import sys

import webextract as we

c = we.WebExtract()
print(datetime.datetime.now(datetime.timezone.utc).isoformat(), "balance:", c.balance())
try:
    r = c.markdown(sys.argv[1] if len(sys.argv) > 1 else "https://example.com")
    print("HTTP", r.meta.status, "billing", r.meta.billing, "free_remaining", r.meta.free_remaining, "words", r.data.get("word_count"))
except we.PaymentRequiredError as e:
    print("HTTP", e.status, type(e).__name__, "reason", e.reason, "free_remaining", e.free_remaining, "networks", ",".join(e.networks), "charged", e.charged)
