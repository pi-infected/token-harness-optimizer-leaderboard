import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, contains_any, emit, truth  # noqa: E402

t = truth("doc-digest.json")["answers"]
a = answer()
results = {q: contains_any(a, kws) for q, kws in t.items()}
emit(sum(results.values()) / len(results),
     " ".join(f"{q}={v}" for q, v in results.items()))
