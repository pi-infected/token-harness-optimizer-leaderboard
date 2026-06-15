import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, TRUTH_DIR, emit, run  # noqa: E402

# the grading suite is hidden from the agent; copy it in only now
hidden_src = TRUTH_DIR / "implement_hidden_test.py"
shutil.copy(hidden_src, WS / "_hidden_test.py")
r = run([sys.executable, "-m", "unittest", "_hidden_test"])
out = r.stderr + r.stdout
m = re.search(r"Ran (\d+) test", out)
ran = int(m.group(1)) if m else 4
failed = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", out))
score = (ran - failed) / ran if ran else 0.0
emit(score, f"hidden tests ran={ran} failed={failed} -> {ran - failed}/{ran}")
