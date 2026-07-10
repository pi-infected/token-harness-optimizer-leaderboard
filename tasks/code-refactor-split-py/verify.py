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
# untouched workspace: no split AND tests pass, so award credit only for
# transformation progress: 0 untouched, 0.5 split-but-red, 1.0 split and green.
score = 1.0 if (split_done and passing) else (0.5 if split_done else 0.0)
emit(score,
     f"split={split_done} (modules present {present}); "
     f"tests {'pass' if passing else 'FAIL: ' + (r.stderr or r.stdout)[-200:]}")
