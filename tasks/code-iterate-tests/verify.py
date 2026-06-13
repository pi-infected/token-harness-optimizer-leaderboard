import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth  # noqa: E402

t = truth("code-iterate-tests.json")
if not hashes_intact(WS, t["test_hashes"]):
    emit(0.0, "tests were modified or deleted")
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
ok = r.returncode == 0
emit(1.0 if ok else 0.0,
     "suite passed" if ok else (r.stderr or r.stdout)[-400:])
