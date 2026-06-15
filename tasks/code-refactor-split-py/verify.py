import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth  # noqa: E402

t = truth("code-refactor-split-py.json")
if not hashes_intact(WS, t["frozen_hashes"]):
    emit(0.0, "the test file was modified — not allowed")
pkg = WS / "shapes"
exp = t["expected_modules"]
present = [m for m in exp if (pkg / f"{m}.py").exists()]
split_done = (pkg.is_dir() and (pkg / "__init__.py").exists()
              and len(present) == len(exp)
              and not (WS / "shapes.py").exists())
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
passing = r.returncode == 0
emit((int(split_done) + int(passing)) / 2,
     f"split={split_done} (modules present {present}); "
     f"tests {'pass' if passing else 'FAIL: ' + (r.stderr or r.stdout)[-200:]}")
