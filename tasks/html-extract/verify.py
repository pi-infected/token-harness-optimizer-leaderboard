import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit, truth  # noqa: E402
t = truth("html-extract.json")
a = answer()
al = a.lower()
year_ok = t["founded_year"] in a
ceo_ok = t["ceo_name"].lower() in al
# price/rate/weight: match the number, tolerate surrounding $, Hz, g, commas
pro_ok = t["pro_plan_price"] in a.replace(",", "")
rate_ok = t["sampling_rate_hz"] in a.replace(",", "")
weight_ok = t["net_weight_grams"] in a.replace(",", "")
score = (year_ok + ceo_ok + pro_ok + rate_ok + weight_ok) / 5
emit(score, f"year={year_ok} ceo={ceo_ok} pro={pro_ok} "
            f"rate={rate_ok} weight={weight_ok}")
