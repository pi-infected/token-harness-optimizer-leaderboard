#!/usr/bin/env python3
"""THOL learned-hook: a PostToolUse hook that compresses Bash output by scoring
each line with the trained salience model (research/train_scorer.py) and
dropping the low-value ones. Pure stdlib — recomputes the standardized logistic
score from scorer.json. Reads transcript_path to get the task prompt for the
context-overlap feature.

Contract (Claude Code PostToolUse): stdin JSON has tool_name, tool_input,
tool_response ({stdout,stderr,interrupted,isImage} for Bash), transcript_path.
We emit hookSpecificOutput.updatedToolOutput to replace what the model sees.
Output schema MUST match the tool or it is silently ignored.
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "scorer.json").read_text())
FEATS, MEAN, SCALE = M["feats"], M["mean"], M["scale"]
COEF, B0, THR, MAXL = M["coef"], M["intercept"], M["threshold"], M["maxlines"]

TOKEN = re.compile(r"[A-Za-z0-9_./:-]{4,}")
PATHLIKE = re.compile(r"[/\w.-]+\.[A-Za-z0-9]+|/[\w./-]+")
DECOR = re.compile(r"^[\s\W_]*$")
NUM = re.compile(r"\d")
CAPS = re.compile(r"\b[A-Z]{3,}\b")
KV = re.compile(r"=|:\s*\S")
HEXH = re.compile(r"\b[0-9a-f]{8,}\b")
MIN_LINES = 12          # don't bother compressing tiny outputs


def task_prompt_tokens(transcript_path):
    """First user message in the transcript ≈ the task prompt."""
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "user":
                    msg = ev.get("message") or {}
                    c = msg.get("content")
                    txt = c if isinstance(c, str) else " ".join(
                        b.get("text", "") for b in c if isinstance(b, dict)) \
                        if isinstance(c, list) else ""
                    if txt.strip():
                        return set(t.lower() for t in TOKEN.findall(txt))
    except Exception:
        pass
    return set()


def feats(ln, i, n, ctx_task, ctx_cmd):
    toks = set(TOKEN.findall(ln))
    lt = set(t.lower() for t in toks)
    return [
        min(len(toks), 30) / 30.0,
        min(len(ln), 200) / 200.0,
        i / max(1, n - 1),
        1.0 if i < 3 else 0.0,
        1.0 if i >= n - 3 else 0.0,
        1.0 if DECOR.match(ln) else 0.0,
        0.0,  # is_dup filled by caller
        1.0 if NUM.search(ln) else 0.0,
        1.0 if PATHLIKE.search(ln) else 0.0,
        1.0 if HEXH.search(ln) else 0.0,
        1.0 if CAPS.search(ln) else 0.0,
        1.0 if KV.search(ln) else 0.0,
        (len(lt & ctx_task) / len(lt)) if lt else 0.0,
        (len(lt & ctx_cmd) / len(lt)) if lt else 0.0,
        0.0, 1.0, 0.0, 0.0,   # tool one-hots: Bash
    ], lt


def keep_line(fv):
    z = B0 + sum(COEF[j] * (fv[j] - MEAN[j]) / SCALE[j] for j in range(len(fv)))
    return 1.0 / (1.0 + math.exp(-max(-30, min(30, z)))) >= THR


def compress(text, ctx_task, ctx_cmd):
    lines = text.splitlines()
    n = len(lines)
    if n < MIN_LINES:
        return text, 0, n
    seen = set()
    kept = []
    for i, ln in enumerate(lines):
        fv, _ = feats(ln, i, n, ctx_task, ctx_cmd)
        fv[6] = 1.0 if ln.strip() in seen else 0.0
        seen.add(ln.strip())
        if keep_line(fv):
            kept.append(ln)
    if not kept:                       # safety floor: never drop everything
        return text, 0, n
    dropped = n - len(kept)
    if dropped <= 0:
        return text, 0, n
    out = "\n".join(kept)
    out += f"\n… [learned-hook elided {dropped}/{n} low-salience lines; re-run for full output]"
    return out, dropped, n


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("tool_name") != "Bash":
        return
    resp = data.get("tool_response") or {}
    if isinstance(resp, str):
        stdout, rest = resp, {}
    elif isinstance(resp, dict):
        stdout, rest = resp.get("stdout", ""), resp
    else:
        return
    if not stdout or not stdout.strip():
        return
    ctx_task = task_prompt_tokens(data.get("transcript_path", ""))
    cmd = (data.get("tool_input") or {}).get("command", "")
    ctx_cmd = set(t.lower() for t in TOKEN.findall(cmd))
    new_stdout, dropped, n = compress(stdout, ctx_task, ctx_cmd)
    if dropped <= 0:
        return                          # nothing to do → leave original
    updated = {
        "stdout": new_stdout,
        "stderr": rest.get("stderr", "") if isinstance(rest, dict) else "",
        "interrupted": rest.get("interrupted", False) if isinstance(rest, dict) else False,
        "isImage": rest.get("isImage", False) if isinstance(rest, dict) else False,
    }
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedToolOutput": updated}}))


if __name__ == "__main__":
    main()
