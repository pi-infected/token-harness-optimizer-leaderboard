import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth  # noqa: E402

t = truth("code-migration-py-xl.json")
if not hashes_intact(WS, t["frozen_hashes"]):
    emit(0.0, "a frozen file (net.py / legacy_http.py / tests) was modified")
app = WS / "webtools" / "app"
leftovers = [p.name for p in sorted(app.glob("*.py"))
             if "legacy_http" in p.read_text()]
migrated = not leftovers
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
passing = r.returncode == 0
# untouched workspace: legacy imports remain AND tests pass (legacy still
# works), so award credit only for migration progress: 0 untouched,
# 0.5 migrated-but-red, 1.0 migrated and green.
score = 1.0 if (migrated and passing) else (0.5 if migrated else 0.0)
emit(score,
     f"legacy imports left: {leftovers or 'none'}; tests "
     f"{'pass' if passing else 'FAIL: ' + (r.stderr or r.stdout)[-300:]}")
