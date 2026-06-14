#!/usr/bin/env python3
"""What is the input-token budget of a CONTROL session actually made of?

Two views, control runs only:
 (A) CONTENT composition — token volume (chars/4) of each category present in the
     transcript: the task prompt, tool results (by tool), the model's own
     thinking / text / tool-call args. This is what the conversation is built
     from (and re-sent/cached every turn).
 (B) REAL usage totals from the result events (input / cache-read / cache-creation
     / output) — to ground (A) and show where the billed tokens really are.

Note: Claude Code's system prompt + tool-schema definitions are NOT in the
transcript (internal), so (A) omits that fixed per-turn overhead; (B) captures
its effect via the token counts.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"


def tk(s):
    return len(s) // 4


def main():
    content = collections.Counter()       # category -> content tokens (chars/4)
    usage = collections.Counter()         # input/cache_read/cache_creation/output
    nruns = 0
    for rd in sorted(RUNS.glob("control__*")):
        tp, mp = rd / "transcript.jsonl", rd / "run.json"
        if not (tp.exists() and mp.exists()):
            continue
        if json.loads(mp.read_text()).get("status") != "ok":
            continue
        nruns += 1
        names = {}
        seen_prompt = False
        for line in tp.open():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            t = ev.get("type")
            if t == "assistant":
                for b in (ev.get("message") or {}).get("content") or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "thinking":
                        content["assistant_thinking"] += tk(b.get("thinking", ""))
                    elif b.get("type") == "text":
                        content["assistant_text"] += tk(b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        names[b.get("id")] = b.get("name", "?")
                        content["assistant_tool_call_args"] += tk(json.dumps(b.get("input") or {}))
            elif t == "user":
                c = (ev.get("message") or {}).get("content")
                if isinstance(c, str):
                    content["task_prompt" if not seen_prompt else "user_text"] += tk(c)
                    seen_prompt = True
                elif isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            txt = b.get("content")
                            txt = txt if isinstance(txt, str) else json.dumps(txt)
                            nm = names.get(b.get("tool_use_id"), "?")
                            cat = "toolresult_Bash" if nm == "Bash" else \
                                "toolresult_Read" if nm == "Read" else \
                                f"toolresult_{nm}"
                            content[cat] += tk(txt)
            elif t == "result":
                u = ev.get("usage") or {}
                usage["input"] += u.get("input_tokens", 0) or 0
                usage["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
                usage["cache_creation"] += u.get("cache_creation_input_tokens", 0) or 0
                usage["output"] += u.get("output_tokens", 0) or 0

    print(f"control runs: {nruns}\n")
    tot = sum(content.values())
    print(f"(A) CONTENT composition of the transcript ({tot:,} tok total, {tot//max(1,nruns):,}/run):")
    for cat, v in content.most_common():
        print(f"  {cat:<26} {v:>9,}  {v/tot*100:4.1f}%")
    print()
    tu = sum(usage.values())
    print(f"(B) REAL billed usage across all control runs ({tu:,} tok):")
    for k in ("cache_read", "input", "cache_creation", "output"):
        print(f"  {k:<16} {usage[k]:>12,}  {usage[k]/max(1,tu)*100:4.1f}%")
    print(f"\n  fresh input (input+cache_creation, paid once each): "
          f"{(usage['input']+usage['cache_creation'])/max(1,tu)*100:.1f}%   "
          f"cache_read (context re-read every turn): {usage['cache_read']/max(1,tu)*100:.1f}%")


if __name__ == "__main__":
    main()
