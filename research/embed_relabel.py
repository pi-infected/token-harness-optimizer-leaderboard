#!/usr/bin/env python3
"""Strengthen the 'needed line' label with embeddings (tokenade's bundled
model2vec potion-code-16M), then re-train the line scorer and compare to the
lexical (token-overlap) label.

Idea (per the design): a line is 'needed' if its embedding is semantically close
to some DOWNSTREAM chunk — max cosine(line, later-event) >= threshold — which
catches paraphrase / semantic reuse that token overlap misses. Scoped to BASH
outputs only (the surface we actually compress; we do NOT filter Read).

  python3 research/embed_relabel.py
"""
import re
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dataset import RUNS, TOKEN, DECOR, PATHLIKE, load_events, event_text, text_of
from model2vec import StaticModel

MODEL_PATH = "/home/infected/.cursor-tutor/projects/tokenade/crates/tokenade-core/assets/model2vec/potion-code-16M"
NUM = re.compile(r"\d"); CAPS = re.compile(r"\b[A-Z]{3,}\b"); KV = re.compile(r"=|:\s*\S")
HEXH = re.compile(r"\b[0-9a-f]{8,}\b")
MAXLINES = 200
m = StaticModel.from_pretrained(MODEL_PATH)


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + 1e-9)


def feats(ln, i, n, dup):
    toks = set(TOKEN.findall(ln))
    return [min(len(toks), 30)/30., min(len(ln), 200)/200., i/max(1, n-1),
            1. if i < 3 else 0., 1. if i >= n-3 else 0., 1. if DECOR.match(ln) else 0.,
            dup, 1. if NUM.search(ln) else 0., 1. if PATHLIKE.search(ln) else 0.,
            1. if HEXH.search(ln) else 0., 1. if CAPS.search(ln) else 0.,
            1. if KV.search(ln) else 0.]


def main():
    import json
    X, lex, cos_scores, runs = [], [], [], []
    seen_runs = 0
    for rd in sorted(RUNS.iterdir()):
        if not rd.is_dir():
            continue
        mp, tp = rd / "run.json", rd / "transcript.jsonl"
        if not (mp.exists() and tp.exists()):
            continue
        meta = json.loads(mp.read_text())
        if meta.get("status") != "ok":
            continue
        evs = load_events(tp)
        # map tool_use_id -> name (to find Bash outputs)
        names = {}
        for e in evs:
            if e.get("type") == "assistant":
                for b in (e.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        names[b.get("id")] = b.get("name")
        # lexical downstream suffix sets
        ev_tok = [set(TOKEN.findall(event_text(e))) for e in evs]
        suf = [set() for _ in range(len(evs)+1)]
        for i in range(len(evs)-1, -1, -1):
            suf[i] = suf[i+1] | ev_tok[i]
        # embed each event's text once (downstream candidates)
        etexts = [event_text(e)[:1000] for e in evs]
        eemb = unit(np.asarray(m.encode([t if t.strip() else " " for t in etexts])))
        had = False
        for i, e in enumerate(evs):
            if e.get("type") != "user":
                continue
            for b in (e.get("message") or {}).get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                if names.get(b.get("tool_use_id")) != "Bash":
                    continue
                out = text_of(b.get("content"))
                if not out.strip():
                    continue
                lines = out.splitlines() or [out]
                if len(lines) > MAXLINES:
                    lines = lines[:MAXLINES//2] + lines[-MAXLINES//2:]
                n = len(lines)
                lemb = unit(np.asarray(m.encode([l if l.strip() else " " for l in lines])))
                down = eemb[i+1:] if i+1 < len(eemb) else None
                seen = set()
                for li, ln in enumerate(lines):
                    dup = 1. if ln.strip() in seen else 0.; seen.add(ln.strip())
                    X.append(feats(ln, li, n, dup))
                    lex.append(1 if (set(TOKEN.findall(ln)) & suf[i+1]) else 0)
                    c = float((lemb[li] @ down.T).max()) if down is not None and len(down) else 0.0
                    cos_scores.append(c)
                    runs.append(str(meta.get("run_id")))
                had = True
        seen_runs += 1 if had else 0
    X = np.array(X); lex = np.array(lex); cos = np.array(cos_scores); runs = np.array(runs)
    print(f"runs with Bash output: {seen_runs}   bash lines: {len(X)}")
    print(f"lexical needed-rate: {lex.mean():.2f}   cos: mean={cos.mean():.2f} p50={np.median(cos):.2f}")
    # calibrate embed threshold so its positive rate matches the lexical one (fair compare)
    thr = float(np.quantile(cos, 1 - lex.mean()))
    emb = (cos >= thr).astype(int)
    print(f"embed threshold (matched prevalence) = {thr:.3f}   embed needed-rate: {emb.mean():.2f}")
    print(f"label agreement lexical vs embed: {(lex == emb).mean()*100:.0f}%")

    # train a scorer on each label, compare (split by run)
    import hashlib
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score
    def h(s): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)
    val = np.array([h(r) % 5 == 0 for r in runs])
    sc = StandardScaler().fit(X[~val])
    for name, y in (("lexical", lex), ("embed", emb)):
        if len(set(y[~val])) < 2:
            continue
        clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(sc.transform(X[~val]), y[~val])
        p = clf.predict_proba(sc.transform(X[val]))[:, 1]
        # self-consistency: predict the SAME label on held-out runs
        auc = roc_auc_score(y[val], p)
        # operating: thr for 0.95 train-recall
        ptr = clf.predict_proba(sc.transform(X[~val]))[:, 1]
        t = 0.0
        for q in sorted(np.unique(np.round(ptr, 3))):
            if y[~val][ptr >= q].sum()/max(1, y[~val].sum()) >= 0.95: t = q
            else: break
        keep = p >= t
        rec = y[val][keep].sum()/max(1, y[val].sum()); comp = 1-keep.mean()
        print(f"  scorer[{name:>7}]: VAL AUC={auc:.3f}  @0.95-recall: recall={rec:.2f} compression={comp*100:.0f}%")


if __name__ == "__main__":
    main()
