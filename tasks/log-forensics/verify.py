import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, int_in_text, truth  # noqa: E402

t = truth("log-forensics.json")
a = answer()
count_ok = int_in_text(a, t["count_5xx"])
ip_ok = t["top_ip"] in a
path_ok = "checkout" in a.lower()
hour = t["spike_hour"]
hour_ok = bool(re.search(rf"(?<!\d){hour}(?::\d{{2}})?(?!\d)", a)
               or re.search(r"\b2\s?p\.?m\.?\b", a, re.I))
emit((count_ok + ip_ok + path_ok + hour_ok) / 4,
     f"count={count_ok} ip={ip_ok} path={path_ok} hour={hour_ok}")
