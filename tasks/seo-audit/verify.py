import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, contains_any, emit, truth  # noqa: E402

report_path = WS / "seo_report.md"
if not report_path.exists():
    emit(0.0, "seo_report.md missing")
report = report_path.read_text().lower()
issues = truth("seo-audit.json")["issues"]
found, missed = [], []
for issue in issues:
    # an issue counts as found if the affected file is named near-verbatim
    # and any of its descriptor keywords appears anywhere in the report
    if issue["file"].lower() in report and contains_any(report, issue["kws"]):
        found.append(issue["id"])
    else:
        missed.append(issue["id"])
emit(len(found) / len(issues), f"found={found}\nmissed={missed}")
