import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit  # noqa: E402

doc = WS / "ANSWERS.md"
if not doc.exists():
    emit(0.0, "ANSWERS.md missing")
text = doc.read_text()

# Split into numbered answers (tolerate `1.`, `1)`, `**1.**` …).
answers = {}
for m in re.finditer(r"^\W*(\d{1,2})[.)]\s*(.+)$", text, re.M):
    answers.setdefault(int(m.group(1)), m.group(2).strip())

# Per-question acceptance regexes (case-insensitive), curated against the
# pinned tree: paginator.py ELLIPSIS "…" · csrf.py CSRF_SECRET_LENGTH=32 ·
# hashers.py iterations=1_800_000 · dispatcher.py weak=True ·
# sessions get_random_string(32, lowercase+digits) · storage.py md5 [:12] ·
# migration.py "auto_%s"/"initial" · engine.py string_if_invalid="" ·
# validators.py schemes http/https/ftp/ftps.
CHECKS = {
    1: [r"…", r"\\u2026", r"horizontal ellipsis"],
    2: [r"\b32\b"],
    3: [r"1[,._ ]?800[,._ ]?000", r"1\.8\s*million"],
    4: [r"\bweak\b"],
    5: [r"\b32\b.*(lower|a-z).*(digit|0-9)|\b32\b.*(digit|0-9).*(lower|a-z)"],
    6: [r"md-?5.*\b12\b|\b12\b.*md-?5"],
    7: [r"auto_?", r"\bauto\b.*timestamp|timestamp.*\bauto\b"],
    8: [r"\binitial\b"],
    9: [r"empty(\s+string)?|^\s*[\"']{2}\s*$|[\"']{2}"],
    10: [r"http\b.*https.*ftp\b.*ftps|ftps.*ftp\b.*https.*http\b"],
}

good, detail = 0, []
for q, pats in CHECKS.items():
    a = answers.get(q, "")
    hit = any(re.search(p, a, re.I) for p in pats)
    good += hit
    detail.append(f"{q}:{'ok' if hit else 'MISS'}")

score = good / len(CHECKS)
emit(score, f"{good}/{len(CHECKS)} correct — " + " ".join(detail))
