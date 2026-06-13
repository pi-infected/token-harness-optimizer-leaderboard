import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit  # noqa: E402

a = answer()
file_ok = "core.py" in a
fn_ok = "resolve_envvar_value" in a or "value_from_envvar" in a
setting_ok = "auto_envvar_prefix" in a
score = (file_ok + fn_ok + setting_ok) / 3
emit(score, f"file={file_ok} fn={fn_ok} setting={setting_ok}")
