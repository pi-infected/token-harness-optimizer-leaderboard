#!/usr/bin/env python3
"""THOL learned-hook: a PostToolUse hook that compresses Bash AND Read output by
scoring each line with the trained salience model and dropping low-value lines.
Pure stdlib — recomputes the standardized logistic score from scorer.json. Reads
transcript_path to get the task prompt for the context-overlap feature.

Bash tool_response = {stdout,stderr,interrupted,isImage}; Read tool_response is a
line-numbered string ("123\\tcontent"). We mirror the input shape in
updatedToolOutput, or Claude Code silently ignores it (built-in tools).
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "scorer.json").read_text())
MEAN, SCALE, COEF, B0, THR = M["mean"], M["scale"], M["coef"], M["intercept"], M["threshold"]

TOKEN = re.compile(r"[A-Za-z0-9_./:-]{4,}")
PATHLIKE = re.compile(r"[/\w.-]+\.[A-Za-z0-9]+|/[\w./-]+")
DECOR = re.compile(r"^[\s\W_]*$")
NUM = re.compile(r"\d")
CAPS = re.compile(r"\b[A-Z]{3,}\b")
KV = re.compile(r"=|:\s*\S")
HEXH = re.compile(r"\b[0-9a-f]{8,}\b")
LNPREFIX = re.compile(r"^\s*\d+\t")     # Read's "123\tcontent" line-number prefix
MIN_LINES = 12


def prompt_tokens(path):
    try:
        with open(path) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "user":
                    c = (ev.get("message") or {}).get("content")
                    txt = c if isinstance(c, str) else " ".join(
                        b.get("text", "") for b in c if isinstance(b, dict)) \
                        if isinstance(c, list) else ""
                    if txt.strip():
                        return set(t.lower() for t in TOKEN.findall(txt))
    except Exception:
        pass
    return set()


def keep_line(ln, i, n, ctx_task, ctx_cmd, dup, is_read):
    body = LNPREFIX.sub("", ln) if is_read else ln
    toks = set(TOKEN.findall(body))
    lt = set(t.lower() for t in toks)
    fv = [
        min(len(toks), 30) / 30.0,
        min(len(body), 200) / 200.0,
        i / max(1, n - 1),
        1.0 if i < 3 else 0.0,
        1.0 if i >= n - 3 else 0.0,
        1.0 if DECOR.match(body) else 0.0,
        dup,
        1.0 if NUM.search(body) else 0.0,
        1.0 if PATHLIKE.search(body) else 0.0,
        1.0 if HEXH.search(body) else 0.0,
        1.0 if CAPS.search(body) else 0.0,
        1.0 if KV.search(body) else 0.0,
        (len(lt & ctx_task) / len(lt)) if lt else 0.0,
        (len(lt & ctx_cmd) / len(lt)) if lt else 0.0,
        1.0 if is_read else 0.0,          # t_read
        0.0 if is_read else 1.0,          # t_bash
        0.0, 0.0,                          # t_edit, t_mcp
    ]
    z = B0 + sum(COEF[j] * (fv[j] - MEAN[j]) / SCALE[j] for j in range(len(fv)))
    return 1.0 / (1.0 + math.exp(-max(-30, min(30, z)))) >= THR


def compress(text, ctx_task, ctx_cmd, is_read):
    lines = text.splitlines()
    n = len(lines)
    if n < MIN_LINES:
        return None
    seen, kept = set(), []
    for i, ln in enumerate(lines):
        key = ln.strip()
        dup = 1.0 if key in seen else 0.0
        seen.add(key)
        if keep_line(ln, i, n, ctx_task, ctx_cmd, dup, is_read):
            kept.append(ln)
    dropped = n - len(kept)
    if not kept or dropped <= 0:
        return None
    out = "\n".join(kept)
    out += f"\n… [learned-hook elided {dropped}/{n} low-salience lines; re-run for full output]"
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tname = data.get("tool_name")
    if tname not in ("Bash", "Read"):
        return
    resp = data.get("tool_response")
    ctx_task = prompt_tokens(data.get("transcript_path", ""))
    inp = data.get("tool_input") or {}
    ctx_cmd = set(t.lower() for t in TOKEN.findall(
        (inp.get("command") or inp.get("file_path") or "")))
    is_read = (tname == "Read")

    # Preserve every original key and replace only the text field, so the
    # output schema matches exactly (built-in tools silently ignore mismatches).
    if tname == "Bash":                       # {stdout,stderr,interrupted,isImage,...}
        if not isinstance(resp, dict):
            return
        new = compress(resp.get("stdout", ""), ctx_task, ctx_cmd, False)
        if new is None:
            return
        upd = dict(resp); upd["stdout"] = new
    else:                                      # Read: {type, file:{filePath,content,...}}
        if not (isinstance(resp, dict) and isinstance(resp.get("file"), dict)):
            return
        content = resp["file"].get("content")
        if not isinstance(content, str):
            return
        new = compress(content, ctx_task, ctx_cmd, True)
        if new is None:
            return
        upd = dict(resp); upd["file"] = dict(resp["file"]); upd["file"]["content"] = new
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "updatedToolOutput": upd}}))


if __name__ == "__main__":
    main()
