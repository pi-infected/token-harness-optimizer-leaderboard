import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth  # noqa: E402

t = truth("code-migration-py.json")
if not hashes_intact(WS, t["frozen_hashes"]):
    emit(0.0, "a frozen file (net.py / legacy_http.py / tests) was modified")
app = WS / "webtools" / "app"
leftovers = [p.name for p in sorted(app.glob("*.py"))
             if "legacy_http" in p.read_text()]
migrated = not leftovers
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
passing = r.returncode == 0
emit((migrated + passing) / 2,
     f"legacy imports left: {leftovers or 'none'}; tests "
     f"{'pass' if passing else 'FAIL: ' + (r.stderr or r.stdout)[-300:]}")
