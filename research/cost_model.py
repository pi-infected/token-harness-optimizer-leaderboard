#!/usr/bin/env python3
"""Cost model: what does one tokenade MCP tool call actually cost end-to-end?

The router's real objective is end-to-end cost, not whether a result was
referenced (RESEARCH.md). Here we quantify the marginal cost: regress each run's
cost RATIO vs control (which removes the per-task baseline) on the number of
tokenade tool calls in that run, across the MCP-using tokenade family. The slope
is "added cost-ratio per tool call" — the bar a call must clear to be worth it.

  python3 research/cost_model.py
"""
import collections
import sqlite3
import statistics as st
from pathlib import Path

import numpy as np

DB = Path(__file__).resolve().parent.parent / "results.sqlite"
MCP_FAMILY = ("tokenade", "tokenade-forced", "tok-mcponly")


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    # control mean successful cost per task = the denominator
    ctrl = collections.defaultdict(list)
    for r in c.execute("SELECT task,total_cost_usd cost FROM runs "
                        "WHERE status='ok' AND success=1 AND competitor='control'"):
        ctrl[r["task"]].append(r["cost"])
    ctrl_mean = {t: st.mean(v) for t, v in ctrl.items() if v}

    xs, ys = [], []
    rows = list(c.execute(
        "SELECT task,competitor,competitor_tool_calls ctc,total_cost_usd cost "
        "FROM runs WHERE status='ok' AND success=1 AND competitor IN (?,?,?)",
        MCP_FAMILY))
    for r in rows:
        base = ctrl_mean.get(r["task"])
        if base and base > 0:
            xs.append(r["ctc"] or 0)
            ys.append(r["cost"] / base)
    x = np.array(xs, float); y = np.array(ys, float)
    print(f"runs: {len(x)}   tool-call range: {int(x.min())}–{int(x.max())}, "
          f"mean {x.mean():.1f}")

    # OLS y = a + b*x
    b, a = np.polyfit(x, y, 1)
    yhat = a + b * x
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    # bootstrap CI on slope
    rng = np.random.default_rng(0)
    slopes = []
    for _ in range(5000):
        idx = rng.integers(0, len(x), len(x))
        slopes.append(np.polyfit(x[idx], y[idx], 1)[0])
    lo, hi = np.percentile(slopes, [2.5, 97.5])
    print(f"\ncost ratio  ≈ {a:.3f} + {b:.4f} × (tokenade tool calls)   R²={r2:.2f}")
    print(f"  marginal cost per tool call: {b*100:+.1f}% of a control session "
          f"[95% CI {lo*100:+.1f}%, {hi*100:+.1f}%]")
    print(f"  intercept {a:.3f}: a 0-tool-call tokenade session is ~{(a-1)*100:+.0f}% "
          "vs control (standing hook/overhead).")

    # binned view
    print("\nmean cost ratio by tool-call bucket:")
    buck = collections.defaultdict(list)
    for xi, yi in zip(x, y):
        k = "0" if xi == 0 else "1-3" if xi <= 3 else "4-9" if xi <= 9 else "10+"
        buck[k].append(yi)
    for k in ("0", "1-3", "4-9", "10+"):
        if buck[k]:
            print(f"  {k:>4} calls: ratio {st.mean(buck[k]):.2f}  (n={len(buck[k])})")
    print("\nimplication: a tool call must SAVE more than its marginal cost to be "
          "worth it; on this battery few do — hence 'call fewer tools'.")


if __name__ == "__main__":
    main()
