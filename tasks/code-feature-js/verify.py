import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import TRUTH_DIR, WS, emit, run  # noqa: E402

hidden = WS / "__thol_hidden.test.js"
shutil.copy(TRUTH_DIR / "jsfeature_hidden.test.js", hidden)
r = run(["node", "--test", hidden.name])
out = r.stdout + r.stderr
m_pass = re.search(r"^# pass (\d+)", out, re.M)
m_fail = re.search(r"^# fail (\d+)", out, re.M)
if m_pass and m_fail:
    p, f = int(m_pass.group(1)), int(m_fail.group(1))
    score = p / (p + f) if (p + f) else 0.0
else:
    score = 1.0 if r.returncode == 0 else 0.0
emit(score, f"hidden tests rc={r.returncode}\n" + out[-400:])
