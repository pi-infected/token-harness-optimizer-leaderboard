#!/usr/bin/env python3
"""Mine THOL run transcripts into a Tier-1 (compression) training dataset.

For every tool OUTPUT in every successful run, we look *forward* in the same
trajectory to find which of its lines/tokens are actually used later (referenced
in reasoning, quoted in the final answer, or re-fetched). From that we derive:

  oracle_keep_ratio = |lines actually needed downstream| / |lines in the output|

i.e. the fraction that a *lossless* compactor would have had to keep. The gap to
1.0 is the compression that was genuinely on the table; the gap between that and
what a competitor actually delivered is the learnable signal (see RESEARCH.md).

Heuristic, recall-oriented v1 (over-keeps rather than over-drops). Writes
research/dataset/decision_points.jsonl and prints descriptive stats. Raw outputs
are NOT emitted into the row (only sizes + labels); pointers stay to the run.
"""
import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "research" / "dataset"
TOKEN = re.compile(r"[A-Za-z0-9_./:-]{4,}")        # ids, paths, numbers, hashes
PATHLIKE = re.compile(r"[/\w.-]+\.[A-Za-z0-9]+|/[\w./-]+")


def est_tokens(s):
    return max(1, len(s) // 4)


def text_of(content):
    """tool_result.content may be a string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict):
                out.append(b.get("text") or b.get("content") or "")
            else:
                out.append(str(b))
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
    """Salient text the model emitted/consumed at this event (for downstream
    reference detection): assistant thinking/text, tool_use commands, final
    result answer. NOT tool_result outputs (those are separate outputs)."""
    t = ev.get("type")
    parts = []
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
    """A path/file the command operates on, for crude re-fetch detection."""
    if not command:
        return None
    m = PATHLIKE.search(command)
    return m.group(0) if m else None


def process_run(run_dir, comp_kind):
    meta_p = run_dir / "run.json"
    tr_p = run_dir / "transcript.jsonl"
    if not (meta_p.exists() and tr_p.exists()):
        return []
    meta = json.loads(meta_p.read_text())
    if meta.get("status") != "ok":
        return []
    evs = load_events(tr_p)

    # index tool_use by id (name + command), in order
    tool_use = {}
    for ev in evs:
        if ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    cmd = inp.get("command") or inp.get("file_path") or \
                        inp.get("path") or inp.get("pattern") or ""
                    tool_use[b.get("id")] = (b.get("name", "?"), str(cmd))

    # per-event salient text, to build forward (downstream) token sets fast
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

    records = []
    for i, ev in enumerate(evs):
        if ev.get("type") != "user":
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_result":
                continue
            out = text_of(b.get("content"))
            lines = out.splitlines() or [out]
            if not out.strip():
                continue
            tname, cmd = tool_use.get(b.get("tool_use_id"), ("?", ""))
            # downstream token universe (everything emitted after this event)
            downstream = set()
            for j in range(i + 1, len(evs)):
                downstream |= ev_tokens[j]
            # which lines are "needed" downstream (recall-oriented)
            needed = 0
            ref_tokens = set()
            for ln in lines:
                toks = set(TOKEN.findall(ln))
                hit = toks & downstream
                if hit:
                    needed += 1
                    ref_tokens |= hit
            keep_ratio = needed / len(lines) if lines else 1.0
            # crude re-fetch: same primary file/arg touched again later
            arg = primary_arg(cmd)
            refetched = False
            if arg:
                for j in range(i + 1, len(evs)):
                    if any(arg in c for c in ev_cmds[j]):
                        refetched = True
                        break
            records.append({
                "run_id": meta.get("run_id"),
                "task": meta.get("task"),
                "competitor": meta.get("competitor"),
                "comp_kind": comp_kind,
                "rep": meta.get("rep"),
                "turn_index": i,
                "claude_version": meta.get("claude_version"),
                "model": meta.get("model"),
                "tool_name": tname,
                "command": cmd[:200],
                "output_tokens_raw": est_tokens(out),
                "output_lines": len(lines),
                "needed_lines": needed,
                "oracle_keep_ratio": round(keep_ratio, 4),
                "referenced_tokens": len(ref_tokens),
                "refetched": refetched,
            })
    return records


# competitor kind: how it intercepts (for later analysis)
KIND = {
    "control": "none", "claude-token-efficient": "claude_md",
    "rtk": "hook", "squeez": "hook", "tok-hooksonly": "hook",
    "tokenade": "hook+mcp", "tok-mcponly": "mcp", "serena": "mcp",
    "lean-ctx": "mcp", "codegraph": "mcp", "token-optimizer-mcp": "mcp",
    "code-review-graph": "mcp", "claude-mem": "none", "claude-context": "mcp",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out_f = (OUT / "decision_points.jsonl").open("w")
    n_records = 0
    runs_seen = 0
    by_tool = defaultdict(list)
    by_comp_keep = defaultdict(list)
    refetch_by_comp = defaultdict(lambda: [0, 0])
    big_drop = []  # large outputs with low keep ratio = compression opportunity
    for run_dir in sorted(RUNS.iterdir()):
        if not run_dir.is_dir():
            continue
        comp = run_dir.name.split("__")[0]
        recs = process_run(run_dir, KIND.get(comp, "?"))
        if recs:
            runs_seen += 1
        for r in recs:
            out_f.write(json.dumps(r) + "\n")
            n_records += 1
            by_tool[r["tool_name"]].append(r["oracle_keep_ratio"])
            by_comp_keep[r["competitor"]].append(r["oracle_keep_ratio"])
            refetch_by_comp[r["competitor"]][0] += 1 if r["refetched"] else 0
            refetch_by_comp[r["competitor"]][1] += 1
            if r["output_lines"] >= 30:
                big_drop.append(r["oracle_keep_ratio"])
    out_f.close()

    print(f"runs processed: {runs_seen}   decision points: {n_records}")
    print(f"dataset: {OUT / 'decision_points.jsonl'}\n")
    allkeep = [k for v in by_comp_keep.values() for k in v]
    if allkeep:
        print(f"oracle_keep_ratio overall: mean={st.mean(allkeep):.2f} "
              f"median={st.median(allkeep):.2f}  → ~{(1-st.mean(allkeep))*100:.0f}% "
              f"of output lines were never referenced downstream (lossless "
              f"compression headroom)")
    if big_drop:
        print(f"on large outputs (>=30 lines, n={len(big_drop)}): "
              f"mean keep={st.mean(big_drop):.2f} "
              f"→ ~{(1-st.mean(big_drop))*100:.0f}% droppable losslessly")
    print("\nkeep-ratio by tool that produced the output (lower = more droppable):")
    for t, v in sorted(by_tool.items(), key=lambda x: st.mean(x[1])):
        if len(v) >= 20:
            print(f"  {t:<28} n={len(v):<5} mean_keep={st.mean(v):.2f}")
    print("\nre-fetch rate by competitor (compaction dropped something needed):")
    for c, (hit, tot) in sorted(refetch_by_comp.items(),
                                key=lambda x: -x[1][0] / max(1, x[1][1])):
        print(f"  {c:<24} {hit}/{tot} = {hit/max(1,tot)*100:.0f}%")


if __name__ == "__main__":
    main()
