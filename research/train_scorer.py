#!/usr/bin/env python3
"""A small per-line salience scorer: predict whether a line of tool output will
be needed downstream, from features available AT compaction time (line
intrinsics + overlap with the task prompt / producing command). No downstream
information is used as a feature — that is the label.

Logistic regression (tiny, interpretable, hook-deployable). Split is BY RUN to
avoid leakage. Evaluated on a held-out validation sample against the heuristic
baselines and the lossless oracle.

  python3 research/train_scorer.py
"""
import re
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dataset import (RUNS, KIND, TOKEN, DECOR, HASHY, PATHLIKE,
                           load_events, event_text, text_of)

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
NUM = re.compile(r"\d")
CAPS = re.compile(r"\b[A-Z]{3,}\b")
KV = re.compile(r"=|:\s*\S")
MAXLINES = 200          # cap per output (head100+tail100) to bound huge CSVs
FEATS = ["n_salient", "len", "rel_pos", "is_head", "is_tail", "is_decor",
         "is_dup", "has_num", "has_path", "has_hash", "has_caps", "has_kv",
         "ctx_task", "ctx_cmd", "t_read", "t_bash", "t_edit", "t_mcp"]


def task_tokens():
    d = {}
    for p in TASKS.glob("*/prompt.md"):
        d[p.parent.name] = set(TOKEN.findall(p.read_text().lower()))
    return d


def featurize_run(run_dir, taskprompts):
    meta_p, tr_p = run_dir / "run.json", run_dir / "transcript.jsonl"
    if not (meta_p.exists() and tr_p.exists()):
        return []
    import json
    meta = json.loads(meta_p.read_text())
    if meta.get("status") != "ok":
        return []
    evs = load_events(tr_p)
    tool_use = {}
    for ev in evs:
        if ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    cmd = inp.get("command") or inp.get("file_path") or \
                        inp.get("path") or inp.get("pattern") or ""
                    tool_use[b.get("id")] = (b.get("name", "?"), str(cmd))
    ev_tokens = [set(TOKEN.findall(event_text(ev))) for ev in evs]
    suffix = [set() for _ in range(len(evs) + 1)]
    for i in range(len(evs) - 1, -1, -1):
        suffix[i] = suffix[i + 1] | ev_tokens[i]
    ctx_task = taskprompts.get(meta.get("task"), set())
    rows = []
    for i, ev in enumerate(evs):
        if ev.get("type") != "user":
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_result":
                continue
            out = text_of(b.get("content"))
            if not out.strip():
                continue
            lines = out.splitlines() or [out]
            if len(lines) > MAXLINES:
                lines = lines[:MAXLINES // 2] + lines[-MAXLINES // 2:]
            tname, cmd = tool_use.get(b.get("tool_use_id"), ("?", ""))
            cmd_tokens = set(TOKEN.findall(cmd.lower()))
            downstream = suffix[i + 1]
            n = len(lines)
            seen = set()
            tk = "read" if tname == "Read" else "bash" if tname == "Bash" else \
                "edit" if tname in ("Edit", "Write", "MultiEdit") else \
                "mcp" if tname.startswith("mcp__") else "other"
            for li, ln in enumerate(lines):
                toks = set(TOKEN.findall(ln))
                ltoks = set(t.lower() for t in toks)
                label = 1 if (toks & downstream) else 0
                dup = 1.0 if ln.strip() in seen else 0.0
                seen.add(ln.strip())
                f = [
                    min(len(toks), 30) / 30.0,
                    min(len(ln), 200) / 200.0,
                    li / max(1, n - 1),
                    1.0 if li < 3 else 0.0,
                    1.0 if li >= n - 3 else 0.0,
                    1.0 if DECOR.match(ln) else 0.0,
                    dup,
                    1.0 if NUM.search(ln) else 0.0,
                    1.0 if PATHLIKE.search(ln) else 0.0,
                    1.0 if re.search(r"\b[0-9a-f]{8,}\b", ln) else 0.0,
                    1.0 if CAPS.search(ln) else 0.0,
                    1.0 if KV.search(ln) else 0.0,
                    (len(ltoks & ctx_task) / len(ltoks)) if ltoks else 0.0,
                    (len(ltoks & cmd_tokens) / len(ltoks)) if ltoks else 0.0,
                    1.0 if tk == "read" else 0.0,
                    1.0 if tk == "bash" else 0.0,
                    1.0 if tk == "edit" else 0.0,
                    1.0 if tk == "mcp" else 0.0,
                ]
                rows.append((meta.get("run_id"), f, label))
    return rows


def main():
    cache = ROOT / "research" / "dataset" / "features.npz"
    if cache.exists() and "--rebuild" not in sys.argv:
        d = np.load(cache, allow_pickle=True)
        X, y, runs = d["X"], d["y"], d["runs"]
        print(f"loaded cached features: lines={len(y)}  needed_rate={y.mean():.2f}"
              f"  (use --rebuild to re-extract)")
    else:
        tp = task_tokens()
        X, y, runs = [], [], []
        seen_runs = 0
        for run_dir in sorted(RUNS.iterdir()):
            if not run_dir.is_dir():
                continue
            rows = featurize_run(run_dir, tp)
            if rows:
                seen_runs += 1
            for rid, f, lab in rows:
                X.append(f); y.append(lab); runs.append(rid)
        X = np.array(X); y = np.array(y); runs = np.array(runs)
        np.savez(cache, X=X, y=y, runs=runs)
        print(f"runs={seen_runs}  lines={len(y)}  needed_rate={y.mean():.2f}  "
              f"(features cached -> research/dataset/features.npz)")

    # split BY RUN (no leakage): 80/20 by a STABLE hash of run_id (hashlib, not
    # Python's per-process-salted hash() — so the split is reproducible).
    import hashlib
    def _h(s):
        return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16)
    uniq = sorted(set(map(str, runs)))
    val_runs = set(r for r in uniq if _h(r) % 5 == 0)
    runs = np.array([str(r) for r in runs])
    val = np.array([r in val_runs for r in runs])
    Xtr, ytr, Xv, yv = X[~val], y[~val], X[val], y[val]
    print(f"train lines={len(ytr)}  val lines={len(yv)}  "
          f"({len(uniq)-len(val_runs)} train runs / {len(val_runs)} val runs)")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, average_precision_score
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    clf.fit(sc.transform(Xtr), ytr)
    pv = clf.predict_proba(sc.transform(Xv))[:, 1]
    print(f"\nVALIDATION  ROC-AUC={roc_auc_score(yv, pv):.3f}  "
          f"AP={average_precision_score(yv, pv):.3f}")

    # operating curve: keep lines with score >= threshold.
    # recall = needed lines kept / needed lines ; compression = 1 - kept fraction
    print("\nscorer operating points (val): keep lines scored >= thr")
    print(f"  {'thr':>5} {'recall':>7} {'compression':>11}")
    order = np.argsort(-pv)
    need = yv.sum()
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
        keep = pv >= thr
        rec = yv[keep].sum() / need if need else 1.0
        comp = 1 - keep.mean()
        print(f"  {thr:>5.2f} {rec:>7.2f} {comp*100:>9.0f}%")
    # pick threshold on TRAIN to hit recall>=0.95, report on VAL (honest)
    ptr = clf.predict_proba(sc.transform(Xtr))[:, 1]
    thrs = np.unique(np.round(ptr, 3))
    chosen = 0.0
    for thr in sorted(thrs):
        rec_tr = ytr[ptr >= thr].sum() / max(1, ytr.sum())
        if rec_tr >= 0.95:
            chosen = thr
        else:
            break
    keep = pv >= chosen
    rec = yv[keep].sum() / need if need else 1.0
    comp = 1 - keep.mean()
    print(f"\nOperating point @train-recall>=0.95  (thr={chosen:.3f}):")
    print(f"  VAL recall={rec:.2f}  compression={comp*100:.0f}%")
    print(f"  vs baselines (B2 salient ~0.96 recall / 6% comp) and "
          f"oracle headroom (~47%, 65% on large)")

    # stronger model on the same features: is it worth the deployment cost?
    from sklearn.ensemble import HistGradientBoostingClassifier
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1,
                                        max_leaf_nodes=31, class_weight="balanced")
    gb.fit(Xtr, ytr)                       # trees: no scaling needed
    pgb, pgb_tr = gb.predict_proba(Xv)[:, 1], gb.predict_proba(Xtr)[:, 1]
    g_thr = 0.0
    for thr in sorted(np.unique(np.round(pgb_tr, 3))):
        if ytr[pgb_tr >= thr].sum() / max(1, ytr.sum()) >= 0.95:
            g_thr = thr
        else:
            break
    gkeep = pgb >= g_thr
    print(f"\nGBM (HistGradientBoosting) VAL ROC-AUC={roc_auc_score(yv, pgb):.3f}  "
          f"AP={average_precision_score(yv, pgb):.3f}")
    print(f"  @train-recall>=0.95 (thr={g_thr:.3f}): VAL recall="
          f"{gkeep[yv == 1].mean():.2f}  compression={(1-gkeep.mean())*100:.0f}%")
    print("  (logreg stays the deployed model unless GBM is materially better —"
          " the stdlib hook needs the linear form)")

    print("\ntop features (logreg coef, standardized):")
    for name, c in sorted(zip(FEATS, clf.coef_[0]), key=lambda x: -abs(x[1]))[:8]:
        print(f"  {name:<10} {c:+.2f}")

    # persist for the hook: scaler params + coef + threshold (no sklearn needed
    # at inference — the hook re-implements the linear score in pure Python)
    import json
    model = {
        "feats": FEATS, "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(),
        "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0]),
        "threshold": float(chosen), "maxlines": MAXLINES,
    }
    (ROOT / "research" / "dataset" / "scorer.json").write_text(json.dumps(model))
    print(f"\nsaved model -> research/dataset/scorer.json (thr={chosen:.3f})")


if __name__ == "__main__":
    main()
