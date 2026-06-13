import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit  # noqa: E402

doc = WS / "ARCHITECTURE.md"
if not doc.exists():
    emit(0.0, "ARCHITECTURE.md missing")
text = doc.read_text()
real = {p.name for p in WS.rglob("*.go")
        if "_test" not in p.name and ".git" not in p.parts}
mentioned = sorted(n for n in real if n in text)
core_ok = "command.go" in mentioned
long_enough = len(text) >= 1200
score = min(1.0, len(mentioned) / 8) * 0.7 + 0.2 * core_ok + 0.1 * long_enough
emit(score, f"{len(mentioned)} real files cited: {mentioned[:12]}")
