import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, int_in_text, truth

t = truth("log-needle-zh.json")
a = answer()
low = a.lower()

checks = {
    "digest": t["checkout_digest"] in low,
    "openssl": t["openssl_version"] in a,
    "trace": t["bad_trace"] in low,
    "port": int_in_text(a, t["payments_port"]),
    "commit": t["commit"].lower() in low,
}
score = sum(1 for v in checks.values() if v) / len(checks)
emit(score, " ".join(f"{k}={v}" for k, v in checks.items()))
