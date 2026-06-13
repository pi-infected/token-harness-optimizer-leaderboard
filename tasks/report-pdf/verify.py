import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, answer, emit, run, truth  # noqa: E402

t = truth("report-pdf.json")
a = answer()
pdf = WS / "report.pdf"
pdf_valid = pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-" \
    and pdf.stat().st_size > 1500
pdf_text_ok = False
if pdf_valid and shutil.which("pdftotext"):
    r = run(["pdftotext", str(pdf), "-"])
    pdf_text_ok = t["top_region"].lower() in r.stdout.lower()
region_ok = t["top_region"].lower() in a.lower()
product_ok = t["top_product_units"].lower() in a.lower()
month_ok = t["best_month_name"].lower() in a.lower()
score = 0.3 * pdf_valid + 0.1 * pdf_text_ok + \
    0.2 * region_ok + 0.2 * product_ok + 0.2 * month_ok
emit(score, f"pdf={pdf_valid} pdf_text={pdf_text_ok} region={region_ok} "
            f"product={product_ok} month={month_ok}")
