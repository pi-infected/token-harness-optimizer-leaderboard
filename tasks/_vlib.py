"""Shared helpers for task verifiers.

Protocol: a verifier is run as `python3 verify.py` with env vars
  WORKSPACE   - the run workspace (post-session)
  ANSWER_FILE - file containing the agent's final reply text
  TRUTH_DIR   - fixtures/truth (never visible to the agent)
It prints `score=<0..1>` plus free-form `detail=` lines, and exits 0
(a non-zero exit means the verifier itself broke, not that the task failed).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WS = Path(os.environ["WORKSPACE"])
TRUTH_DIR = Path(os.environ["TRUTH_DIR"])
ANSWER_FILE = os.environ.get("ANSWER_FILE", "")


def answer() -> str:
    try:
        return Path(ANSWER_FILE).read_text()
    except OSError:
        return ""


def truth(name: str):
    return json.loads((TRUTH_DIR / name).read_text())


def emit(score: float, detail: str = ""):
    print(f"score={max(0.0, min(1.0, score)):.4f}")
    if detail:
        for line in detail.splitlines():
            print(f"detail={line}")
    sys.exit(0)


def run(cmd, cwd=None, timeout=300):
    return subprocess.run(cmd, cwd=str(cwd or WS), timeout=timeout,
                          capture_output=True, text=True)


def contains_any(text: str, kws) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in kws)


def int_in_text(text: str, value: int) -> bool:
    """True if `value` appears as a standalone number (commas/spaces ok)."""
    variants = {str(value), f"{value:,}", f"{value:,}".replace(",", " "),
                f"{value:,}".replace(",", " ")}
    return any(re.search(rf"(?<![\d.]){re.escape(v)}(?![\d.])", text)
               for v in variants)


def sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes_intact(root: Path, expected: dict) -> bool:
    for rel, h in expected.items():
        p = root / rel
        if not p.exists() or sha(p) != h:
            return False
    return True
