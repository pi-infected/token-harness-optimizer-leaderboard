import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, int_in_text, truth  # noqa: E402

t = truth("log-needle.json")
a = answer()
low = a.lower()

# Each needle is a rare, UNIQUE, verbatim value buried in near-duplicate noise.
# Hashes / uuids are matched case-insensitively (agents sometimes upper-case);
# numbers use int_in_text so a 4-digit value can't false-match inside a hex run.
checks = {
    "digest": t["checkout_digest"] in low,
    "openssl": t["openssl_version"] in a,
    "trace": t["bad_trace"] in low,
    "port": int_in_text(a, t["payments_port"]),
    "commit": t["commit"].lower() in low,
}
score = sum(1 for v in checks.values() if v) / len(checks)
emit(score, " ".join(f"{k}={v}" for k, v in checks.items()))
