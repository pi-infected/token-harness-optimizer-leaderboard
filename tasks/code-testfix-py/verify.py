import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth  # noqa: E402

t = truth("code-testfix-py.json")
if not hashes_intact(WS, t["frozen_hashes"]):
    emit(0.0, "the test file was modified — not allowed")
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
out = r.stderr + r.stdout
m = re.search(r"Ran (\d+) test", out)
ran = int(m.group(1)) if m else t["n_tests"]
failed = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", out))
score = (ran - failed) / ran if ran else 0.0
emit(score, f"ran={ran} failed={failed} -> {ran - failed}/{ran} passing")
