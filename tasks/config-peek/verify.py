import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, truth  # noqa: E402
t = truth("config-peek.json")
a = answer()
port_ok = t["port"] in a
db_ok = t["database_name"].lower() in a.lower()
emit((port_ok + db_ok) / 2, f"port={port_ok} db={db_ok}")
