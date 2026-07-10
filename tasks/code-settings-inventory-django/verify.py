import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit  # noqa: E402

doc = WS / "SETTINGS_INVENTORY.md"
if not doc.exists():
    emit(0.0, "SETTINGS_INVENTORY.md missing")
text = doc.read_text()

# Ground truth: every distinct `settings.NAME` read under django/ (no tests).
pat = re.compile(r"\bsettings\.([A-Z][A-Z0-9_]{2,})\b")
truth = set()
for p in (WS / "django").rglob("*.py"):
    if ".git" in p.parts:
        continue
    try:
        for m in pat.finditer(p.read_text(errors="replace")):
            truth.add(m.group(1))
    except OSError:
        pass

# Parse claimed entries: `NAME — path:line` (tolerate -, –, — separators).
entry = re.compile(
    r"^\s*[-*]?\s*`?([A-Z][A-Z0-9_]{2,})`?\s*[—–-]+\s*`?([\w./-]+\.py):(\d+)`?",
    re.M,
)
claims = {}
for m in entry.finditer(text):
    claims.setdefault(m.group(1), (m.group(2), int(m.group(3))))

if not claims:
    emit(0.0, "no parseable `NAME — path:line` entries")

# Precision: the cited line (±2) really reads settings.NAME.
ok = 0
for name, (rel, ln) in claims.items():
    f = WS / rel
    if not f.exists():
        continue
    lines = f.read_text(errors="replace").splitlines()
    lo, hi = max(0, ln - 3), min(len(lines), ln + 2)
    window = "\n".join(lines[lo:hi])
    if re.search(rf"\bsettings\.{re.escape(name)}\b", window):
        ok += 1
precision = ok / len(claims)

# Recall against ground truth, normalised to the asked-for 90.
valid_names = {n for n in claims if n in truth}
recall = min(1.0, len(valid_names) / 90)

score = 0.4 * precision + 0.6 * recall
emit(
    score,
    f"{len(claims)} claimed, {ok} line-verified (precision {precision:.2f}), "
    f"{len(valid_names)}/90 valid distinct (truth={len(truth)})",
)
