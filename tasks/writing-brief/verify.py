import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit  # noqa: E402

p = WS / "post.md"
if not p.exists():
    emit(0.0, "post.md missing")
text = p.read_text()
words = len(re.findall(r"\b\w+\b", text))
words_ok = 700 <= words <= 900
words_close = 630 <= words <= 990
h2 = re.findall(r"^## +(.+?)\s*$", text, re.M)
expected = ["Why pipelines rot", "Choosing what to automate",
            "Keeping CI fast", "FAQ"]
h2_ok = [e.lower() for e in expected] == [h.lower() for h in h2]
h2_partial = sum(e.lower() in [h.lower() for h in h2] for e in expected) / 4
faq = text.lower().split("## faq")[-1] if "## faq" in text.lower() else ""
faq_ok = len(re.findall(r"\?", faq)) >= 3
kws = ["flaky tests", "caching", "parallelization", "code review",
       "deployment"]
kw_frac = sum(k in text.lower() for k in kws) / len(kws)
h1_ok = bool(re.match(r"^# +\S", text.strip()))
score = (0.3 if words_ok else 0.15 if words_close else 0.0) \
    + (0.25 if h2_ok else 0.25 * h2_partial * 0.6) \
    + 0.2 * faq_ok + 0.15 * kw_frac + 0.1 * h1_ok
emit(score, f"words={words} h2_exact={h2_ok} faq={faq_ok} kw={kw_frac:.2f} "
            f"h1={h1_ok}")
