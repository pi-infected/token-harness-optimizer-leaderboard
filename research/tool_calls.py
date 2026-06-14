#!/usr/bin/env python3
"""Tier-2 (routing) dataset: every tokenade MCP tool call in the trajectories,
labelled with a usefulness proxy — was the call's RESULT actually referenced
downstream, and was it NOT immediately followed by a recovery call
(expand_ref/search_stash, which would mean the call didn't deliver what was
needed)? Data-first, like the compression track: characterise which tokenade
tools are worth calling before training a router.

Writes research/dataset/tool_calls.jsonl and prints per-tool stats.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dataset import RUNS, TOKEN, load_events, event_text, text_of

OUT = Path(__file__).resolve().parent.parent / "research" / "dataset"
RECOVERY = ("expand_ref", "search_stash")


def process(run_dir):
    meta_p, tr_p = run_dir / "run.json", run_dir / "transcript.jsonl"
    if not (meta_p.exists() and tr_p.exists()):
        return []
    meta = json.loads(meta_p.read_text())
    if meta.get("status") != "ok":
        return []
    evs = load_events(tr_p)
    # suffix salient-token sets (downstream universe)
    ev_tokens = [set(TOKEN.findall(event_text(e))) for e in evs]
    suffix = [set() for _ in range(len(evs) + 1)]
    for i in range(len(evs) - 1, -1, -1):
        suffix[i] = suffix[i + 1] | ev_tokens[i]
    # map tool_use_id -> (name, turn) for tokenade calls; collect recovery turns
    calls, recov = {}, []
    for i, ev in enumerate(evs):
        if ev.get("type") != "assistant":
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                name = b.get("name", "")
                if name.startswith("mcp__tokenade__"):
                    calls[b.get("id")] = (name.split("__")[-1], i, b.get("input") or {})
                    if any(r in name for r in RECOVERY):
                        recov.append(i)
    # pair with results, label usefulness
    rows = []
    for i, ev in enumerate(evs):
        if ev.get("type") != "user":
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_result":
                continue
            cid = b.get("tool_use_id")
            if cid not in calls:
                continue
            tool, turn, inp = calls[cid]
            out = text_of(b.get("content"))
            toks = set(TOKEN.findall(out))
            referenced = bool(toks & suffix[i + 1])
            recov_after = any(t > i for t in recov)
            rows.append({
                "run_id": meta.get("run_id"), "task": meta.get("task"),
                "competitor": meta.get("competitor"), "tool": tool,
                "result_tokens": max(1, len(out) // 4),
                "referenced_downstream": referenced,
                "recovery_after": recov_after,
                "useful": referenced and not recov_after,
            })
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = (OUT / "tool_calls.jsonl").open("w")
    per = defaultdict(lambda: {"n": 0, "useful": 0, "ref": 0, "toks": 0})
    n = 0
    for run_dir in sorted(RUNS.iterdir()):
        if not run_dir.is_dir() or "tokenade" not in run_dir.name.split("__")[0]:
            continue
        for r in process(run_dir):
            f.write(json.dumps(r) + "\n")
            n += 1
            p = per[r["tool"]]
            p["n"] += 1
            p["useful"] += r["useful"]
            p["ref"] += r["referenced_downstream"]
            p["toks"] += r["result_tokens"]
    f.close()
    print(f"tokenade tool calls: {n}   -> {OUT / 'tool_calls.jsonl'}\n")
    print(f"{'tool':<22} {'calls':>6} {'useful%':>8} {'referenced%':>11} {'avg_tokens':>10}")
    for t, p in sorted(per.items(), key=lambda x: -x[1]["n"]):
        if p["n"] >= 3:
            print(f"{t:<22} {p['n']:>6} {p['useful']/p['n']*100:>7.0f}% "
                  f"{p['ref']/p['n']*100:>10.0f}% {p['toks']//p['n']:>10}")


if __name__ == "__main__":
    main()
