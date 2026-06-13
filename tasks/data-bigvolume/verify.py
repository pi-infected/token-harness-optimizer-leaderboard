import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, int_in_text, truth  # noqa: E402
t = truth("data-bigvolume.json")
a = answer()
al = a.lower()
country_ok = t["top_country_revenue"].lower() in al
event_ok = t["most_frequent_event"].lower() in al
month_ok = (t["best_revenue_month_name"].lower() in al
            or t["best_revenue_month_num"] in a)
count_ok = int_in_text(a, t["purchases_over_500usd"])
emit((country_ok + event_ok + month_ok + count_ok) / 4,
     f"country={country_ok} event={event_ok} month={month_ok} "
     f"count={count_ok}")
