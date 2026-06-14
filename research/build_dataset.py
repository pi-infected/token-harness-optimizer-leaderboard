#!/usr/bin/env python3
"""Mine THOL run transcripts into a Tier-1 (compression) training dataset, with
refined re-fetch labels and heuristic salience baselines measured vs the oracle.

For every tool OUTPUT in every successful run we look forward in the trajectory
to find which lines are actually used later. From that:

  oracle_keep_ratio = |lines needed downstream| / |lines|   (lossless target)

Refined loss signals (see RESEARCH.md):
  refetched_strong  = an explicit recovery call (expand_ref / search_stash) fired
                      after this output  → compaction folded something needed
                      (clean signal, tokenade family).
  excess re-access  = per-task refetch_rate(comp) - refetch_rate(control), which
                      nets out the agent's normal re-reading (control's 50%).

Heuristic baselines (predict the keep-set without seeing the future), scored vs
the oracle by recall-of-needed-lines and achieved compression:
  B1 denoise  = drop blank / decorative / duplicate lines (+ keep head & tail)
  B2 salient  = keep only lines bearing a salient token (+ head & tail)

Writes research/dataset/decision_points.jsonl and prints stats. Raw outputs are
not emitted into rows.
"""
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "research" / "dataset"
TOKEN = re.compile(r"[A-Za-z0-9_./:-]{4,}")
PATHLIKE = re.compile(r"[/\w.-]+\.[A-Za-z0-9]+|/[\w./-]+")
HASHY = re.compile(r"\b[0-9a-f]{8,}\b|\b\d+\b|[A-Z]{3,}|[\w.-]+=[^\s]|:\s*\S")
DECOR = re.compile(r"^[\s\W_]*$")          # blank / only punctuation-decoration
RECOVERY = ("expand_ref", "search_stash")  # explicit "recover folded bytes" tools
HEAD_TAIL = 3


def est_tokens(s):
    return max(1, len(s) // 4)


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            out.append(b.get("text") or b.get("content") or "" if isinstance(b, dict) else str(b))
        return "\n".join(out)
    return str(content or "")


def load_events(path):
    evs = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    evs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return evs


def event_text(ev):
    t, parts = ev.get("type"), []
    if t == "assistant":
        for b in (ev.get("message") or {}).get("content") or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") in ("text", "thinking"):
                parts.append(b.get("text") or b.get("thinking") or "")
            elif b.get("type") == "tool_use":
                parts.append(json.dumps(b.get("input") or {}))
    elif t == "result":
        parts.append(str(ev.get("result") or ""))
    return "\n".join(parts)


def primary_arg(command):
    if not command:
        return None
    m = PATHLIKE.search(command)
    return m.group(0) if m else None


def baseline_keep(lines):
    """Return (b1_keep_idxs, b2_keep_idxs) — sets of kept line indices."""
    n = len(lines)
    head_tail = set(range(min(HEAD_TAIL, n))) | set(range(max(0, n - HEAD_TAIL), n))
    b1, b2, seen = set(head_tail), set(head_tail), set()
    for i, ln in enumerate(lines):
        s = ln.strip()
        # B1 denoise: keep unless blank/decorative or an exact duplicate
        if not DECOR.match(ln) and s not in seen:
            b1.add(i)
        seen.add(s)
        # B2 salient: keep only lines bearing a salient token
        if HASHY.search(ln):
            b2.add(i)
    return b1, b2


def process_run(run_dir, comp_kind):
    meta_p, tr_p = run_dir / "run.json", run_dir / "transcript.jsonl"
    if not (meta_p.exists() and tr_p.exists()):
        return []
    meta = json.loads(meta_p.read_text())
    if meta.get("status") != "ok":
        return []
    evs = load_events(tr_p)

    tool_use = {}
    recovery_turns = []          # event indices where a recovery tool was called
    for idx, ev in enumerate(evs):
        if ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    name = b.get("name", "?")
                    inp = b.get("input") or {}
                    cmd = inp.get("command") or inp.get("file_path") or \
                        inp.get("path") or inp.get("pattern") or ""
                    tool_use[b.get("id")] = (name, str(cmd))
                    if any(r in name for r in RECOVERY):
                        recovery_turns.append(idx)

    ev_tokens = [set(TOKEN.findall(event_text(ev))) for ev in evs]
    ev_cmds = []
    for ev in evs:
        cmds = []
        if ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    cmds.append(str(inp.get("command") or inp.get("file_path")
                                    or inp.get("path") or ""))
        ev_cmds.append(cmds)

    # suffix token sets (everything emitted strictly after position i)
    suffix = [set() for _ in range(len(evs) + 1)]
    for i in range(len(evs) - 1, -1, -1):
        suffix[i] = suffix[i + 1] | ev_tokens[i]

    records = []
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
            tname, cmd = tool_use.get(b.get("tool_use_id"), ("?", ""))
            downstream = suffix[i + 1]
            needed = set()
            ref_tokens = set()
            for li, ln in enumerate(lines):
                hit = set(TOKEN.findall(ln)) & downstream
                if hit:
                    needed.add(li)
                    ref_tokens |= hit
            nlines = len(lines)
            keep_ratio = len(needed) / nlines if nlines else 1.0

            b1, b2 = baseline_keep(lines)

            def recall(keep):
                return (len(keep & needed) / len(needed)) if needed else 1.0
            # re-fetch (coarse): same primary arg re-touched later
            arg = primary_arg(cmd)
            refetched = bool(arg) and any(
                any(arg in c for c in ev_cmds[j]) for j in range(i + 1, len(evs)))
            # refined: an explicit recovery call fired after this output
            refetched_strong = any(rt > i for rt in recovery_turns)

            records.append({
                "run_id": meta.get("run_id"), "task": meta.get("task"),
                "competitor": meta.get("competitor"), "comp_kind": comp_kind,
                "rep": meta.get("rep"), "turn_index": i,
                "claude_version": meta.get("claude_version"),
                "model": meta.get("model"), "tool_name": tname,
                "command": cmd[:200], "output_tokens_raw": est_tokens(out),
                "output_lines": nlines, "needed_lines": len(needed),
                "oracle_keep_ratio": round(keep_ratio, 4),
                "referenced_tokens": len(ref_tokens),
                "refetched": refetched, "refetched_strong": refetched_strong,
                "b1_keep_ratio": round(len(b1) / nlines, 4),
                "b1_recall": round(recall(b1), 4),
                "b2_keep_ratio": round(len(b2) / nlines, 4),
                "b2_recall": round(recall(b2), 4),
            })
    return records


KIND = {
    "control": "none", "claude-token-efficient": "claude_md",
    "rtk": "hook", "squeez": "hook", "tok-hooksonly": "hook",
    "tokenade": "hook+mcp", "tok-mcponly": "mcp", "serena": "mcp",
    "lean-ctx": "mcp", "codegraph": "mcp", "token-optimizer-mcp": "mcp",
    "code-review-graph": "mcp", "claude-mem": "none", "claude-context": "mcp",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = (OUT / "decision_points.jsonl").open("w")
    n = runs = 0
    keep_all, keep_big = [], []
    b1r, b1k, b2r, b2k = [], [], [], []
    refetch_by_task = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # task->comp->[hit,tot]
    strong_by_comp = defaultdict(lambda: [0, 0])
    for run_dir in sorted(RUNS.iterdir()):
        if not run_dir.is_dir():
            continue
        comp = run_dir.name.split("__")[0]
        recs = process_run(run_dir, KIND.get(comp, "?"))
        runs += 1 if recs else 0
        for r in recs:
            f.write(json.dumps(r) + "\n")
            n += 1
            keep_all.append(r["oracle_keep_ratio"])
            if r["output_lines"] >= 30:
                keep_big.append(r["oracle_keep_ratio"])
            b1r.append(r["b1_recall"]); b1k.append(r["b1_keep_ratio"])
            b2r.append(r["b2_recall"]); b2k.append(r["b2_keep_ratio"])
            rt = refetch_by_task[r["task"]][r["competitor"]]
            rt[0] += 1 if r["refetched"] else 0
            rt[1] += 1
            sc = strong_by_comp[r["competitor"]]
            sc[0] += 1 if r["refetched_strong"] else 0
            sc[1] += 1
    f.close()
    print(f"runs processed: {runs}   decision points: {n}\n")
    print(f"ORACLE (lossless headroom): mean_keep={st.mean(keep_all):.2f} "
          f"→ {(1-st.mean(keep_all))*100:.0f}% droppable; "
          f"large outputs keep={st.mean(keep_big):.2f} "
          f"→ {(1-st.mean(keep_big))*100:.0f}% droppable\n")
    print("HEURISTIC BASELINES vs oracle (recall of needed lines | achieved compression):")
    print(f"  B1 denoise : recall={st.mean(b1r):.2f}  compression={(1-st.mean(b1k))*100:.0f}%")
    print(f"  B2 salient : recall={st.mean(b2r):.2f}  compression={(1-st.mean(b2k))*100:.0f}%")
    print("  (oracle = recall 1.00 at the droppable% above; a good rule keeps recall high)\n")

    print("REFINED RE-FETCH:")
    print("  strong (explicit recovery call after a compacted output):")
    for c, (h, t) in sorted(strong_by_comp.items(), key=lambda x: -x[1][0]/max(1, x[1][1])):
        if h:
            print(f"    {c:<22} {h}/{t} = {h/max(1,t)*100:.0f}%")
    # excess re-access vs control, per task, averaged over tasks
    excess = defaultdict(list)
    for task, comps in refetch_by_task.items():
        if "control" not in comps or comps["control"][1] == 0:
            continue
        cr = comps["control"][0] / comps["control"][1]
        for c, (h, t) in comps.items():
            if c != "control" and t >= 2:
                excess[c].append(h / t - cr)
    print("  excess re-access vs control (mean over tasks; +ve = compaction-induced):")
    for c, v in sorted(excess.items(), key=lambda x: -st.mean(x[1])):
        if KIND.get(c) in ("hook", "hook+mcp") and len(v) >= 5:
            print(f"    {c:<22} {st.mean(v)*100:+.0f} pts  (over {len(v)} tasks)")


if __name__ == "__main__":
    main()
