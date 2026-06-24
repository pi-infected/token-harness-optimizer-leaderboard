import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth

t = truth("code-debug-cascade-py.json")
if not hashes_intact(WS, t["frozen_test_hashes"]):
    emit(0.0, "a frozen test file under tests/ was modified")
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
out = (r.stderr or "") + (r.stdout or "")
ran = re.search(r"Ran (\d+) test", out)
total = int(ran.group(1)) if ran else t["total_tests"]
fails = errs = 0
m = re.search(r"failures=(\d+)", out); fails = int(m.group(1)) if m else 0
m = re.search(r"errors=(\d+)", out);   errs = int(m.group(1)) if m else 0
passed = total - fails - errs
score = 1.0 if r.returncode == 0 else max(0.0, passed / total)
emit(score, f"{passed}/{total} tests pass"
            + ("" if r.returncode == 0 else f"; tail: {out[-300:]}"))
