import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, int_in_text, truth  # noqa: E402

t = truth("data-analysis.json")
a = answer()
al = a.lower()
region_ok = t["top_region"].lower() in al
product_ok = t["top_product_units"].lower() in al
month_ok = t["best_month_name"].lower() in al or t["best_month_num"] in a
count_ok = int_in_text(a, t["orders_over_5000"])
emit((region_ok + product_ok + month_ok + count_ok) / 4,
     f"region={region_ok} product={product_ok} month={month_ok} "
     f"count={count_ok}")
