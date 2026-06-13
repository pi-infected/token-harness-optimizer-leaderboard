import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, truth  # noqa: E402

t = truth("code-debug-cilog.json")
a = answer()
hits = [m for m in t["markers_required"] if m in a]
emit(len(hits) / len(t["markers_required"]), f"markers found: {hits}")
