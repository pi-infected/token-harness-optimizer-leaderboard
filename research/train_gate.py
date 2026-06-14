#!/usr/bin/env python3
"""Per-output GATE: predict how compressible a tool output is (oracle_keep_ratio)
from features available AT hook time — tool/surface + size. Combined with the
end-to-end lesson (compress Bash command-noise, NOT Read file-content, which
triggers re-reads), this decides *whether* to compress an output before the
per-line scorer runs. Reads research/dataset/decision_points.jsonl (fast).

  python3 research/train_gate.py
"""
import hashlib
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DP = ROOT / "research" / "dataset" / "decision_points.jsonl"


def tool_kind(name):
    if name == "Read":
        return "read"
    if name == "Bash":
        return "bash"
    if name in ("Edit", "Write", "MultiEdit"):
        return "edit"
    if str(name).startswith("mcp__"):
        return "mcp"
    return "other"


def main():
    rows = [json.loads(l) for l in DP.open()]
    print(f"decision points: {len(rows)}")
    # per-tool headroom (confirms the surface signal behind the negative result)
    by = {}
    for r in rows:
        by.setdefault(tool_kind(r["tool_name"]), []).append(r["oracle_keep_ratio"])
    print("\nmean oracle_keep_ratio by surface (lower = more compressible):")
    for k, v in sorted(by.items(), key=lambda x: st.mean(x[1])):
        print(f"  {k:<7} n={len(v):<5} keep={st.mean(v):.2f}  (~{(1-st.mean(v))*100:.0f}% droppable)")

    X, y, runs = [], [], []
    for r in rows:
        k = tool_kind(r["tool_name"])
        X.append([
            1.0 if k == "read" else 0.0, 1.0 if k == "bash" else 0.0,
            1.0 if k == "edit" else 0.0, 1.0 if k == "mcp" else 0.0,
            math.log1p(r["output_lines"]), math.log1p(r["output_tokens_raw"]),
        ])
        y.append(r["oracle_keep_ratio"]); runs.append(str(r["run_id"]))
    X, y = np.array(X), np.array(y)

    def h(s):
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)
    val = np.array([h(r) % 5 == 0 for r in runs])
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error
    gb = HistGradientBoostingRegressor(max_iter=200)
    gb.fit(X[~val], y[~val])
    pred = gb.predict(X[val])
    mae = mean_absolute_error(y[val], pred)
    base = mean_absolute_error(y[val], np.full(val.sum(), y[~val].mean()))
    print(f"\nGATE regressor (predict keep_ratio): VAL MAE={mae:.3f} "
          f"(baseline predict-mean MAE={base:.3f})")

    # gate policy eval: 'compress' if predicted droppable is high AND safe surface.
    # safe surface = Bash (Read backfires end-to-end — see RESEARCH.md).
    yv = y[val]
    is_bash = X[val][:, 1] == 1.0
    for thr in (0.4, 0.5, 0.6, 0.7):
        gate = (pred <= thr) & is_bash      # compress only Bash predicted compressible
        if gate.sum():
            avg_actual_keep = yv[gate].mean()
            print(f"  gate(pred_keep<= {thr}, Bash-only): fires on {gate.mean()*100:4.0f}% "
                  f"of outputs; their actual keep={avg_actual_keep:.2f} "
                  f"(~{(1-avg_actual_keep)*100:.0f}% really droppable)")


if __name__ == "__main__":
    main()
