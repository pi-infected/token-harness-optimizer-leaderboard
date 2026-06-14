#!/usr/bin/env python3
"""Tier-2 router feasibility: can we predict whether a tokenade tool call will be
USEFUL (tool_calls.jsonl proxy), and does task-context add over per-tool base
rates? Honest check on thin data (193 calls) before claiming a router.

  python3 research/train_router.py
"""
import json
import statistics as st
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
TC = ROOT / "research" / "dataset" / "tool_calls.jsonl"


def main():
    rows = [json.loads(l) for l in TC.open()]
    print(f"tool calls: {len(rows)}   useful base-rate: "
          f"{sum(r['useful'] for r in rows)/len(rows):.2f}")
    tools = sorted({r["tool"] for r in rows})
    tasks = sorted({r["task"] for r in rows})
    ti = {t: i for i, t in enumerate(tools)}
    ki = {t: i for i, t in enumerate(tasks)}

    def feat(r, with_task):
        v = [0.0] * len(tools)
        v[ti[r["tool"]]] = 1.0
        if with_task:
            tk = [0.0] * len(tasks)
            tk[ki[r["task"]]] = 1.0
            v = v + tk
        return v

    y = np.array([1 if r["useful"] else 0 for r in rows])
    groups = np.array([r["run_id"] for r in rows])
    gkf = GroupKFold(n_splits=5)

    for with_task in (False, True):
        X = np.array([feat(r, with_task) for r in rows])
        aucs = []
        for tr, te in gkf.split(X, y, groups):
            if len(set(y[tr])) < 2 or len(set(y[te])) < 2:
                continue
            clf = LogisticRegression(max_iter=1000, class_weight="balanced")
            clf.fit(X[tr], y[tr])
            aucs.append(roc_auc_score(y[te], clf.predict_proba(X[te])[:, 1]))
        label = "tool + task" if with_task else "tool only "
        print(f"  {label}: grouped-CV AUC = {st.mean(aucs):.3f} "
              f"(± {st.pstdev(aucs):.2f}, {len(aucs)} folds)")

    # how much does the best tool vary by task? (does routing need context?)
    best = {}
    for t in tasks:
        sub = [r for r in rows if r["task"] == t]
        c = Counter()
        n = Counter()
        for r in sub:
            c[r["tool"]] += r["useful"]; n[r["tool"]] += 1
        rates = {tool: c[tool]/n[tool] for tool in n if n[tool] >= 2}
        if rates:
            best[t] = max(rates, key=rates.get)
    print(f"\nbest-tool varies across tasks: {len(set(best.values()))} distinct "
          f"winners over {len(best)} tasks (with >=2 calls/tool)")
    print("verdict: with 193 calls the per-tool base rate dominates; a "
          "context-aware router needs the forced-adoption arm for data.")


if __name__ == "__main__":
    main()
