#!/usr/bin/env python3
"""THOL runner — isolated end-to-end Claude Code sessions per
(competitor x task x repetition), with real token/cost/success measurement.

Isolation model (the host setup is NEVER touched):
- each run gets a fresh CLAUDE_CONFIG_DIR (own settings/hooks/MCP universe;
  only the login credentials are copied in, read-only),
- each run gets a throwaway workspace under runs_root (default /tmp) so no
  ancestor CLAUDE.md can leak into the session context,
- `--strict-mcp-config` guarantees only the competitor's declared MCP
  servers are loaded.
"""
import argparse
import json
import socket
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "bench.config.json").read_text())
TASKS_DIR = ROOT / "tasks"
COMP_DIR = ROOT / "competitors"
FIXTURES_OUT = ROOT / "fixtures" / "out"
TRUTH_DIR = ROOT / "fixtures" / "truth"
REPO_CACHE = ROOT / ".cache" / "repos"
ARTIFACTS = ROOT / "runs"
DB_PATH = ROOT / "results.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  competitor TEXT, task TEXT, rep INTEGER,
  started_at TEXT, model TEXT, claude_version TEXT,
  competitor_version TEXT,
  status TEXT,            -- ok | timeout | claude_error | install_error | skipped
  score REAL, success INTEGER,
  total_cost_usd REAL,
  input_tokens INTEGER, output_tokens INTEGER,
  cache_creation_tokens INTEGER, cache_read_tokens INTEGER,
  num_turns INTEGER, api_duration_ms INTEGER,
  wall_ms INTEGER, setup_ms INTEGER,
  tool_calls INTEGER, competitor_tool_calls INTEGER,
  tool_rounds INTEGER,
  tokenade_claim_weighted INTEGER,  -- what tokenade's own ledger claims it saved this run
  mcp_init_status TEXT,   -- JSON: declared MCP servers' status at session init
  verify_detail TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS mcp_health (
  competitor TEXT, claude_version TEXT, server TEXT,
  checked_at TEXT, status TEXT,     -- ok | fail
  n_tools INTEGER, latency_ms INTEGER, error TEXT,
  PRIMARY KEY (competitor, claude_version, server)
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_tasks():
    tasks = {}
    for tj in sorted(TASKS_DIR.glob("*/task.json")):
        t = json.loads(tj.read_text())
        t["_dir"] = tj.parent
        tasks[t["id"]] = t
    return tasks


def load_competitors():
    comps = {}
    for mj in sorted(COMP_DIR.glob("*/manifest.json")):
        m = json.loads(mj.read_text())
        m["_dir"] = mj.parent
        comps[m["name"]] = m
    return comps


def claude_version(env):
    try:
        r = subprocess.run([CFG["claude_bin"], "--version"], env=env,
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return "unknown"


def ensure_repo(name):
    lock = json.loads((ROOT / "repos.lock.json").read_text())[name]
    dst = REPO_CACHE / name
    if not dst.exists():
        REPO_CACHE.mkdir(parents=True, exist_ok=True)
        print(f"  cloning {lock['url']} @ {lock['commit'][:10]} ...")
        subprocess.run(["git", "clone", "--quiet", lock["url"], str(dst)],
                       check=True)
    head = subprocess.run(["git", "-C", str(dst), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    if head != lock["commit"]:
        subprocess.run(["git", "-C", str(dst), "fetch", "--quiet", "origin",
                        lock["commit"]], check=False)
        subprocess.run(["git", "-C", str(dst), "checkout", "--quiet",
                        lock["commit"]], check=True)
    return dst


def build_workspace(task, ws):
    spec = task.get("workspace") or {}
    if spec.get("fixture"):
        src = FIXTURES_OUT / spec["fixture"]
        if not src.exists():
            sys.exit(f"fixture '{spec['fixture']}' missing — run "
                     f"fixtures/generate_fixtures.py first")
        shutil.copytree(src, ws)
    elif spec.get("repo"):
        shutil.copytree(ensure_repo(spec["repo"]), ws, symlinks=True)
    else:
        ws.mkdir(parents=True)


def setup_config_dir(cfgdir, manifest):
    cfgdir.mkdir(parents=True)
    creds = Path.home() / ".claude" / ".credentials.json"
    if creds.exists():
        shutil.copy(creds, cfgdir / ".credentials.json")
    state = {"hasCompletedOnboarding": True,
             "bypassPermissionsModeAccepted": True}
    (cfgdir / ".claude.json").write_text(json.dumps(state))
    settings = manifest.get("settings") or {}
    (cfgdir / "settings.json").write_text(
        json.dumps(settings, indent=1).replace("${CFG}", str(cfgdir)))
    # files the competitor's installer would place in the global config dir
    # (e.g. a global CLAUDE.md) — copied verbatim from the manifest dir
    for rel in manifest.get("config_files") or []:
        shutil.copy(manifest["_dir"] / rel, cfgdir / Path(rel).name)
    # credentials copied from the real HOME into the sandbox home (license
    # keys, activation files) — never state/cache databases, which would
    # leak memory across runs and bias the benchmark
    for rel in manifest.get("home_files") or []:
        src = Path(os.environ.get("HOME", "")) / rel
        if src.exists():
            dst = cfgdir.parent / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)


def build_env(cfgdir, manifest):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("TOKENADE", "CLAUDE"))}
    # PATH hygiene: host command shims (e.g. a dir wrapping node/python)
    # can silently mute stdio MCP servers spawned through them — strip them.
    # The effective PATH is recorded per run in the env.json artifact.
    # Pin Claude Code to a fixed version. The machine's `claude` symlink can be
    # flipped by CC's auto-updater or a parallel interactive session, silently
    # running a different harness version mid-campaign (a reproducibility hole:
    # cost/turns shift with the version). A bench-owned bin dir holding a
    # `claude` -> versions/<pinned> symlink, prepended to PATH, makes every run
    # use the pinned binary regardless of the global symlink — including edgee,
    # whose `edgee launch claude` resolves `claude` via PATH.
    pin = str(ROOT / ".claude-pin")
    env["PATH"] = pin + ":" + ":".join(
        p for p in env.get("PATH", "").split(":")
        if "/.tokenade/" not in p and p != pin)
    env["HOME"] = str(cfgdir.parent)
    env["CLAUDE_CONFIG_DIR"] = str(cfgdir)
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    env["DISABLE_AUTOUPDATER"] = "1"
    # give every competitor's MCP server the same generous startup window
    env.setdefault("MCP_TIMEOUT", "60000")
    # the sandboxed HOME must not break the host toolchain the sessions use
    real_home = os.environ.get("HOME", "")
    pyenv_root = Path(real_home) / ".pyenv"
    if pyenv_root.exists():
        env.setdefault("PYENV_ROOT", str(pyenv_root))
    env.setdefault("npm_config_cache", str(ROOT / ".cache" / "npm"))
    env.setdefault("UV_CACHE_DIR", str(ROOT / ".cache" / "uv"))
    # Share the HuggingFace model cache across the throwaway HOMEs so tools that
    # pull an ONNX/transformer model (e.g. headroom's Kompress compressor) fetch
    # it once instead of re-downloading per run. Immutable weights → safe to share.
    env.setdefault("HF_HOME", str(ROOT / ".cache" / "hf"))
    env.update({k: v.replace("${CFG}", str(cfgdir))
                for k, v in (manifest.get("env") or {}).items()})
    return env


def parse_stream(transcript_path, manifest):
    """Returns (result_event, tool_calls, competitor_tool_calls, tool_rounds,
    mcp_init_status_json).

    tool_rounds = number of assistant messages carrying >=1 tool_use, i.e. the
    real count of serial tool-call rounds (each one re-reads the whole context).
    This is the true cost driver — the harness `num_turns` field is unreliable
    (observed 2-3 while the transcript holds 17-25 tool rounds). With one
    tool_use per message tool_rounds == tool_calls; they diverge once the model
    batches (parallel tool_use), so adoption shows up as calls > rounds."""
    prefixes = tuple(manifest.get("tool_prefixes") or ())
    markers = manifest.get("bash_command_markers") or []
    result_ev, calls, comp_calls, rounds = None, 0, 0, 0
    init_ev = None
    with transcript_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init" \
                    and init_ev is None:
                init_ev = ev
            elif ev.get("type") == "assistant":
                msg_has_tool = False
                for block in (ev.get("message") or {}).get("content") or []:
                    if block.get("type") != "tool_use":
                        continue
                    msg_has_tool = True
                    calls += 1
                    name = block.get("name", "")
                    if prefixes and name.startswith(prefixes):
                        comp_calls += 1
                    elif name == "Bash" and markers:
                        cmd = (block.get("input") or {}).get("command", "")
                        if any(m in cmd for m in markers):
                            comp_calls += 1
                if msg_has_tool:
                    rounds += 1
            elif ev.get("type") == "result":
                result_ev = ev
    # What the session saw at init: MCP servers connect asynchronously in
    # headless mode (typically still 'pending' here), so record it.
    mcp_init = None
    if init_ev is not None:
        tools = init_ev.get("tools") or []
        mcp_init = json.dumps({
            "servers": init_ev.get("mcp_servers") or [],
            "mcp_tools_at_init": sum(1 for t in tools
                                     if t.startswith("mcp__")),
        })
    return result_ev, calls, comp_calls, rounds, mcp_init


def run_verify(task, ws, answer_file):
    env = dict(os.environ,
               WORKSPACE=str(ws), ANSWER_FILE=str(answer_file),
               TRUTH_DIR=str(TRUTH_DIR))
    r = subprocess.run([sys.executable, str(task["_dir"] / "verify.py")],
                       env=env, capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr
    m = re.search(r"^score=([\d.]+)", r.stdout, re.M)
    score = float(m.group(1)) if m else None
    return score, out


def insert_row(row):
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    # migrate pre-existing tables that lack newer columns
    try:
        con.execute("ALTER TABLE runs ADD COLUMN tool_rounds INTEGER")
    except sqlite3.OperationalError:
        pass  # column already present
    try:
        con.execute("ALTER TABLE runs ADD COLUMN tokenade_claim_weighted INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE runs ADD COLUMN mcp_init_status TEXT")
    except sqlite3.OperationalError:
        pass
    cols = ", ".join(row)
    q = f"INSERT OR REPLACE INTO runs ({cols}) VALUES ({','.join('?' * len(row))})"
    con.execute(q, list(row.values()))
    con.commit()
    con.close()


def run_one(comp, task, rep, args, cver):
    run_id = f"{comp['name']}__{task['id']}__r{rep}__{int(time.time())}"
    base = Path(CFG["runs_root"]) / run_id
    # a full throwaway HOME per run: competitors' installers and hooks that
    # hardcode ~/.claude (or any dotfile) land in the sandbox, never on the
    # host. CLAUDE_CONFIG_DIR is <home>/.claude inside it.
    home = base / "home"
    ws, cfgdir = base / "workspace", home / ".claude"
    art = ARTIFACTS / run_id
    art.mkdir(parents=True, exist_ok=True)
    row = {"run_id": run_id, "competitor": comp["name"], "task": task["id"],
           "rep": rep, "started_at": now_iso(), "model": args.model,
           "claude_version": cver,
           "competitor_version": comp.get("version_pin"),
           "status": "ok", "score": None,
           "success": None, "total_cost_usd": None, "input_tokens": None,
           "output_tokens": None, "cache_creation_tokens": None,
           "cache_read_tokens": None, "num_turns": None,
           "api_duration_ms": None, "wall_ms": None, "setup_ms": 0,
           "tool_calls": None, "competitor_tool_calls": None,
           "tool_rounds": None,
           "tokenade_claim_weighted": None,
           "mcp_init_status": None,
           "verify_detail": None, "error": None}
    env = None
    sub = lambda x: x  # replaced once the run's port is allocated
    try:
        build_workspace(task, ws)
        setup_config_dir(cfgdir, comp)
        env = build_env(cfgdir, comp)
        # one free port per run, substitutable as ${PORT} anywhere the
        # manifest needs it (env, setup/teardown commands, claude_wrap) so
        # back-to-back runs of proxy/gateway competitors never collide.
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]; s.close()
        sub = lambda x: x.replace("${PORT}", str(free_port))
        env = {k: sub(v) for k, v in env.items()}
        # record the exact environment the session ran with
        (art / "env.json").write_text(json.dumps(
            {"PATH": env.get("PATH"), "HOME": env.get("HOME"),
             "port": free_port,
             "manifest_env": {k: env.get(k)
                              for k in (comp.get("env") or {})}}, indent=1))
        claude_md = comp.get("claude_md")
        if comp.get("claude_md_file"):
            claude_md = (comp["_dir"] / comp["claude_md_file"]).read_text()
        if claude_md:
            (ws / "CLAUDE.md").write_text(claude_md)

        for binary in comp.get("requires") or []:
            if not shutil.which(binary, path=env.get("PATH")):
                row.update(status="install_error",
                           error=f"required binary not on PATH: {binary}")
                insert_row(row)
                return row

        t0 = time.monotonic()
        for cmdline in comp.get("setup_commands") or []:
            cmdline = sub(cmdline)
            r = subprocess.run(cmdline, shell=True, cwd=ws, env=env,
                               capture_output=True, text=True, timeout=900)
            (art / "setup.log").open("a").write(
                f"$ {cmdline}\nrc={r.returncode}\n{r.stdout}\n{r.stderr}\n")
            if r.returncode != 0:
                row.update(status="install_error", setup_ms=int(
                    (time.monotonic() - t0) * 1000),
                    error=f"setup command failed: {cmdline}")
                insert_row(row)
                return row
        row["setup_ms"] = int((time.monotonic() - t0) * 1000)

        prompt = (task["_dir"] / "prompt.md").read_text()
        claude_argv = ["-p", prompt,
               "--output-format", "stream-json", "--verbose",
               "--model", args.model,
               "--max-turns", str(task.get("max_turns", 40)),
               "--dangerously-skip-permissions", "--strict-mcp-config"]
        # `claude_wrap` lets a competitor run Claude Code through its own
        # auto-proxy/wrapper (e.g. ["headroom","wrap","claude","--"], which
        # starts the proxy + sets ANTHROPIC_BASE_URL so ALL API traffic is
        # compacted automatically — the tool's primary mode). Without it the
        # tool's official Claude binary is invoked directly.
        wrap = comp.get("claude_wrap")
        if wrap:
            # `${PORT}` in the wrap is substituted with this run's free port
            # so back-to-back wrapped runs never collide on a default fixed
            # port (the failure mode that rc=1'd most of the first headroom
            # re-bench).
            wrap = [sub(t) for t in wrap]
            # Keep --strict-mcp-config (in claude_argv): it blocks the heavy MCP
            # tool-definitions headroom's wrapper auto-registers (serena +
            # codebase-memory + headroom-retrieve) from bloating the context.
            # The proxy still compresses traffic in token mode (inline, no
            # retrieve tool needed) — measured cc -14% on log-needle-zh.
            cmd = wrap + claude_argv
        else:
            cmd = [CFG["claude_bin"]] + claude_argv
        if comp.get("mcp"):
            mcp_file = base / "mcp.json"
            mcp_file.write_text(json.dumps(comp["mcp"], indent=1))
            cmd += ["--mcp-config", str(mcp_file)]

        transcript = art / "transcript.jsonl"
        w0 = time.monotonic()
        try:
            with transcript.open("w") as out:
                p = subprocess.run(cmd, cwd=ws, env=env, stdout=out,
                                   stderr=subprocess.PIPE, text=True,
                                   timeout=task.get("timeout_s", 1200))
            stderr = p.stderr
        except subprocess.TimeoutExpired as e:
            row.update(status="timeout",
                       wall_ms=int((time.monotonic() - w0) * 1000),
                       error=f"timed out after {task.get('timeout_s')}s")
            stderr = (e.stderr or b"").decode() if isinstance(
                e.stderr, bytes) else (e.stderr or "")
            (art / "stderr.log").write_text(stderr)
            insert_row(row)
            return row
        row["wall_ms"] = int((time.monotonic() - w0) * 1000)
        (art / "stderr.log").write_text(stderr or "")

        result_ev, calls, comp_calls, rounds, mcp_init = \
            parse_stream(transcript, comp)
        row.update(tool_calls=calls, competitor_tool_calls=comp_calls,
                   tool_rounds=rounds, mcp_init_status=mcp_init)
        if result_ev is None:
            row.update(status="claude_error",
                       error=f"no result event (rc={p.returncode}); "
                             f"stderr tail: {(stderr or '')[-300:]}")
            insert_row(row)
            return row

        usage = result_ev.get("usage") or {}
        row.update(
            total_cost_usd=result_ev.get("total_cost_usd"),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            cache_creation_tokens=usage.get("cache_creation_input_tokens"),
            cache_read_tokens=usage.get("cache_read_input_tokens"),
            num_turns=result_ev.get("num_turns"),
            api_duration_ms=result_ev.get("duration_api_ms")
            or result_ev.get("duration_ms"))

        answer_file = art / "answer.txt"
        answer_text = result_ev.get("result") or ""
        answer_file.write_text(answer_text)
        # spurious API-level failures (e.g. usage-policy false positives) are
        # infrastructure errors, not task failures: excluded from success
        # stats, visible in the non-ok table, redone on resume
        if result_ev.get("is_error") or answer_text.startswith("API Error"):
            row.update(status="claude_error", error=answer_text[:300])
            insert_row(row)
            return row

        # Reconciliation: capture what tokenade's OWN ledger claims it saved
        # on THIS run (weighted, measured only), so a paired analysis can
        # compare the claim to the real cost delta vs control. Non-tokenade
        # competitors leave no ledger → stays None. Zero API cost.
        row["tokenade_claim_weighted"] = read_tokenade_claim(home)

        score, vout = run_verify(task, ws, answer_file)
        (art / "verify.txt").write_text(vout)
        if score is None:
            row.update(status="claude_error", error="verifier emitted no score")
        else:
            row.update(score=score,
                       success=int(score >= task.get("success_threshold", 1.0)))
        insert_row(row)
        return row
    finally:
        # teardown_commands: best-effort cleanup a competitor needs after the
        # session (e.g. stopping a local gateway/daemon started in setup) —
        # never affects the run's recorded status.
        if env is not None:
            for cmdline in comp.get("teardown_commands") or []:
                cmdline = sub(cmdline)
                try:
                    r = subprocess.run(cmdline, shell=True,
                                       cwd=(ws if ws.exists() else base),
                                       env=env, capture_output=True,
                                       text=True, timeout=60)
                    (art / "teardown.log").open("a").write(
                        f"$ {cmdline}\nrc={r.returncode}\n{r.stdout}\n{r.stderr}\n")
                except Exception as e:
                    (art / "teardown.log").open("a").write(
                        f"$ {cmdline}\nEXC {e}\n")
        (art / "run.json").write_text(json.dumps(row, indent=1))
        if not args.keep_workspaces and base.exists():
            shutil.rmtree(base, ignore_errors=True)


def _handshake_stdio(cmd, cwd, env, timeout_s=60):
    """Raw MCP stdio handshake: initialize + tools/list. Returns
    (ok, n_tools, latency_ms, error)."""
    import select
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "thol-healthcheck", "version": "1"}}}
    t0 = time.monotonic()
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, bufsize=1)
    except OSError as e:
        return False, 0, 0, f"spawn failed: {e}"
    try:
        p.stdin.write(json.dumps(init) + "\n")
        p.stdin.flush()
        deadline = t0 + timeout_s

        def read_json(want_id):
            while time.monotonic() < deadline:
                r, _, _ = select.select([p.stdout], [], [], 0.5)
                if not r:
                    if p.poll() is not None:
                        return None, f"server exited rc={p.returncode}"
                    continue
                line = p.stdout.readline()
                if not line:
                    return None, f"stdout closed (rc={p.poll()})"
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("id") == want_id:
                    return ev, None
            return None, f"no response within {timeout_s}s"

        resp, err = read_json(1)
        if resp is None:
            return False, 0, int((time.monotonic() - t0) * 1000), err
        latency = int((time.monotonic() - t0) * 1000)
        p.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        p.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list",
             "params": {}}) + "\n")
        p.stdin.flush()
        resp, err = read_json(2)
        if resp is None:
            return False, 0, latency, f"tools/list: {err}"
        tools = (resp.get("result") or {}).get("tools") or []
        return True, len(tools), latency, None
    except Exception as e:
        return False, 0, int((time.monotonic() - t0) * 1000), str(e)
    finally:
        try:
            p.kill()
        except Exception:
            pass


def ensure_mcp_health(comp, cver):
    """Handshake every declared MCP server once per (competitor,
    claude_version), cached in mcp_health. A raw stdio handshake in its own
    throwaway sandbox — no Claude session, nothing pre-warmed, so measured
    runs start pristine. Returns {server_name: (ok, error)}."""
    servers = (comp.get("mcp") or {}).get("mcpServers") or {}
    if not servers:
        return {}
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    cached = {r[0]: (r[1] == "ok", r[2]) for r in con.execute(
        "SELECT server, status, error FROM mcp_health "
        "WHERE competitor=? AND claude_version=?", (comp["name"], cver))}
    if set(cached) == set(servers) and all(ok for ok, _ in cached.values()):
        con.close()
        return cached
    # sandbox mirroring run conditions (throwaway HOME + tiny workspace),
    # torn down right after — never reused by an actual run
    base = Path(CFG["runs_root"]) / f"mcp-health__{comp['name']}__{int(time.time())}"
    ws, cfgdir = base / "workspace", base / "home" / ".claude"
    out = {}
    try:
        ws.mkdir(parents=True)
        (ws / "app.py").write_text("def add(a, b):\n    return a + b\n")
        setup_config_dir(cfgdir, comp)
        env = build_env(cfgdir, comp)
        for name, srv in servers.items():
            cmd = [srv["command"]] + list(srv.get("args") or [])
            ok, n_tools, latency, err = _handshake_stdio(cmd, ws, env)
            out[name] = (ok, err)
            con.execute(
                "INSERT OR REPLACE INTO mcp_health VALUES (?,?,?,?,?,?,?,?)",
                (comp["name"], cver, name, now_iso(),
                 "ok" if ok else "fail", n_tools, latency, err))
            print(f"  mcp-health {comp['name']}/{name}: "
                  f"{'OK' if ok else 'FAIL'} tools={n_tools} "
                  f"{latency}ms{' — ' + err if err else ''}")
        con.commit()
    finally:
        con.close()
        shutil.rmtree(base, ignore_errors=True)
    return out


def read_tokenade_claim(home):
    """Weighted measured savings tokenade booked in this run's sandbox HOME
    (input + cache/10 + output*5). None when there's no tokenade ledger."""
    led = Path(home) / ".tokenade" / "gain.jsonl"
    if not led.exists():
        return None
    w = 0.0
    try:
        for line in led.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("est") is True:
                continue
            before = d.get("tokens_before") or 0
            after = d.get("tokens_after") or 0
            saved = d.get("saved")
            saved = (before - after) if saved is None else min(saved, before - after)
            if saved <= 0:
                continue
            io = d.get("io") or "input"
            w += saved * (5.0 if io == "output" else 0.1 if io == "cache" else 1.0)
    except Exception:
        return None
    return int(w)


def reconcile(db_path=None):
    """Compare tokenade's CLAIMED weighted savings to the REAL weighted cost
    delta vs the control arm, per (task, model). Prints a table + a verdict;
    flags any task where the claim diverges from reality by >20%."""
    con = sqlite3.connect(db_path or DB_PATH)
    con.executescript(SCHEMA)
    try:
        con.execute("ALTER TABLE runs ADD COLUMN tokenade_claim_weighted INTEGER")
    except sqlite3.OperationalError:
        pass
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM runs WHERE status='ok' AND success=1").fetchall()]
    con.close()

    def wtok(r):
        return ((r["input_tokens"] or 0)
                + (r["cache_read_tokens"] or 0) / 10.0
                + (r["output_tokens"] or 0) * 5.0)

    # control arm = competitor named 'control' (raw Claude, no optimizer)
    ctrl = {}
    for r in rows:
        if r["competitor"] == "control":
            ctrl.setdefault((r["task"], r["model"]), []).append(wtok(r))
    print(f"{'task':32} {'claim':>12} {'real Δ vs ctrl':>16} {'ratio':>8}  verdict")
    flagged = 0
    for r in rows:
        if r["competitor"] != "tokenade" or r.get("tokenade_claim_weighted") is None:
            continue
        base = ctrl.get((r["task"], r["model"]))
        if not base:
            continue
        real_delta = sum(base) / len(base) - wtok(r)
        claim = r.get("tokenade_claim_weighted")
        ratio = (claim / real_delta) if real_delta > 0 else float("inf")
        ok = real_delta > 0 and 0.8 <= ratio <= 1.2
        if not ok:
            flagged += 1
        print(f"{r['task'][:32]:32} {claim:>12} {real_delta:>16.0f} "
              f"{ratio:>8.2f}  {'OK' if ok else 'DIVERGES>20%'}")
    print(f"\n{flagged} task(s) diverge >20% between tokenade's claim and the "
          f"measured cost delta vs control.")
    return flagged


def select(arg, available, what):
    if arg in (None, "all"):
        return list(available)
    chosen = [x.strip() for x in arg.split(",") if x.strip()]
    unknown = [c for c in chosen if c not in available]
    if unknown:
        sys.exit(f"unknown {what}: {unknown} (available: {list(available)})")
    return chosen


def cmd_run(args):
    tasks, comps = load_tasks(), load_competitors()
    comp_names = select(args.competitors, comps, "competitor")
    task_names = select(args.tasks, tasks, "task")
    for c in comp_names:
        if not comps[c].get("verified", False) and not args.allow_unverified:
            sys.exit(f"competitor '{c}' manifest is not marked verified "
                     f"(install steps not yet validated on this machine). "
                     f"Re-run with --allow-unverified to accept it as-is.")
    # resume support: a run is atomic (its row lands in the DB only on
    # completion), so after any interruption — Ctrl-C, kill, power loss —
    # relaunching the same command skips completed (competitor, task, rep)
    # triples and redoes only what is missing. --rerun forces everything.
    env0 = build_env(Path("/tmp"), {})
    cver = claude_version(env0)
    # Refuse to run if the harness is not the pinned campaign version. Claude
    # Code prunes old builds, which can leave .claude-pin/claude dangling and
    # PATH resolving to another version; since resume is keyed on
    # claude_version, that would start a fresh campaign instead of continuing
    # this one. Fail loudly rather than measure under a different harness.
    want = os.environ.get("THOL_CAMPAIGN")
    if want and not cver.startswith(want):
        sys.exit(f"campaign pin mismatch: THOL_CAMPAIGN={want} but claude is "
                 f"{cver!r}.\nThe .claude-pin/claude symlink is dangling or "
                 f"wrong — repoint it at a {want} binary (npm install --prefix "
                 f".cache/claude-{want.split('.')[-1]} "
                 f"@anthropic-ai/claude-code@{want}), or unset THOL_CAMPAIGN to "
                 f"deliberately start a new campaign at {cver}.")
    # resume is CAMPAIGN-AWARE: only runs recorded under the SAME
    # claude_version count as "done". A new Claude Code release therefore
    # re-measures every cell from scratch instead of silently inheriting the
    # previous version's runs — which is what let earlier campaigns (2.1.170/
    # 172/173) bleed into a 2.1.177 board and bias the medians. Aggregation
    # must likewise scope to one claude_version (see leaderboard.py).
    done_keys = set()
    if DB_PATH.exists() and not args.rerun:
        con = sqlite3.connect(DB_PATH)
        try:
            done_keys = {tuple(r) for r in con.execute(
                "SELECT competitor, task, rep FROM runs "
                "WHERE status='ok' AND claude_version=?", (cver,))}
        except sqlite3.OperationalError:
            pass
        con.close()
    plan = [(c, t, rep) for rep in range(1, args.reps + 1)
            for t in task_names for c in comp_names]
    todo = [k for k in plan if k not in done_keys]
    n = len(todo)
    est = n * CFG["est_cost_per_run_usd"]
    print(f"plan: {len(comp_names)} competitor(s) x {len(task_names)} task(s) "
          f"x {args.reps} rep(s) = {len(plan)} runs; "
          f"{len(plan) - n} already done @ {cver} (resume), {n} to run, "
          f"rough estimate ~${est:.2f}")
    if args.budget_usd:
        print(f"hard budget: ${args.budget_usd:.2f}")
    print(f"model={args.model}  claude={cver}\n")

    # Binary preflight — a competitor whose `requires` binary vanished from
    # PATH (an installer removing a rival, an npm/cargo prune) would otherwise
    # log one install_error per planned run. Check once, skip its cells.
    missing = {c: [b for b in comps[c].get("requires") or []
                   if not shutil.which(b, path=env0.get("PATH"))]
               for c in comp_names}
    absent = {c: b for c, b in missing.items() if b and any(k[0] == c for k in todo)}
    for c, bins in absent.items():
        print(f"!! required binary missing for '{c}': {bins}\n"
              f"   -> its planned runs are SKIPPED. Install it, then relaunch "
              f"(setup/install_competitors.sh).")
    todo = [k for k in todo if k[0] not in absent]

    # MCP preflight — once per (competitor, claude_version), cached in
    # mcp_health; a broken server must fail loudly, not burn API money and
    # surface as fake "0 adoption".
    if not getattr(args, "skip_mcp_healthcheck", False):
        unhealthy = set()
        for c in comp_names:
            if not comps[c].get("mcp") or not any(k[0] == c for k in todo):
                continue
            res = ensure_mcp_health(comps[c], cver)
            bad = {s: e for s, (ok, e) in res.items() if not ok}
            if bad:
                unhealthy.add(c)
                print(f"!! MCP healthcheck FAILED for '{c}': {bad}\n"
                      f"   -> its planned runs are SKIPPED. Fix the install "
                      f"(or force with --skip-mcp-healthcheck).")
        todo = [k for k in todo if k[0] not in unhealthy]

    spent = 0.0
    done = 0
    streak = 0  # consecutive infrastructure failures
    # `plan` interleaves reps so temporal drift (API conditions, model
    # updates) spreads evenly across competitors instead of biasing one
    for c, t, rep in todo:
        if args.budget_usd and spent >= args.budget_usd:
            print(f"budget exhausted (${spent:.2f}) — stopping", flush=True)
            return
        r = run_one(comps[c], tasks[t], rep, args, cver)
        spent += r.get("total_cost_usd") or 0.0
        done += 1
        print(f"[{done}/{n}] {c:>12} | {t:<18} r{rep} -> "
              f"{r['status']:<13} score={r['score']} "
              f"${(r['total_cost_usd'] or 0):.3f} "
              f"turns={r['num_turns']} "
              f"wall={(r['wall_ms'] or 0) / 1000:.0f}s "
              f"(total ${spent:.2f})", flush=True)
        # An environment failure (expired credentials, API outage) hits every
        # run alike and marches through the whole plan in minutes, leaving a
        # campaign of empty rows. Stop on a streak so the cause can be fixed
        # and the campaign resumed.
        streak = streak + 1 if r["status"] == "claude_error" else 0
        if streak >= args.max_consecutive_errors:
            sys.exit(f"\n{streak} consecutive claude_error runs — aborting.\n"
                     f"last error: {(r['error'] or '')[:200]}\n"
                     f"Fix the cause, then relaunch the same command: "
                     f"completed runs are skipped, failed ones are redone.")


def _control_turns(task_id, cver, comp_name="control"):
    """num_turns of every OK run for this (competitor, task) at this CC
    version — the campaign-scoped sample the stabilization rule grows."""
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    rows = con.execute(
        "SELECT num_turns FROM runs WHERE competitor=? AND task=? "
        "AND status='ok' AND claude_version=? AND num_turns IS NOT NULL",
        (comp_name, task_id, cver)).fetchall()
    con.close()
    return [r[0] for r in rows]


def _is_stable(turns, nmin, tol):
    """Mean of num_turns is 'stable' once we have >= nmin samples and the
    standard error of the mean is within `tol` of the mean (relative). A
    zero-variance task converges immediately at nmin."""
    import statistics
    n = len(turns)
    if n < nmin:
        return False, None
    m = statistics.mean(turns)
    if m == 0:
        return True, 0.0
    sd = statistics.pstdev(turns)
    rel_sem = (sd / (n ** 0.5)) / m
    return rel_sem <= tol, rel_sem


def cmd_stabilize(args):
    """Run the control baseline for each task in increments, stopping each
    task as soon as the mean number of turns stabilizes (rel. SEM <= --tol)
    or --nmax reps are reached. Campaign-scoped to the current CC version."""
    tasks = load_tasks()
    comps = load_competitors()
    comp = comps[args.competitors if args.competitors not in (None, "all")
                 else "control"]
    task_names = select(args.tasks, tasks, "task")
    env0 = build_env(Path("/tmp"), {})
    cver = claude_version(env0)
    print(f"stabilize: {comp['name']} @ {cver}  model={args.model}\n"
          f"  criterion: nmin={args.nmin} nmax={args.nmax} "
          f"rel_SEM<={args.tol}\n")
    if comp.get("mcp") and not getattr(args, "skip_mcp_healthcheck", False):
        res = ensure_mcp_health(comp, cver)
        bad = {s: e for s, (ok, e) in res.items() if not ok}
        if bad:
            sys.exit(f"MCP healthcheck failed for '{comp['name']}': {bad}")
    if args.budget_usd:
        print(f"hard budget: ${args.budget_usd:.2f}\n")
    spent = 0.0
    summary = []
    for t in task_names:
        turns = _control_turns(t, cver, comp["name"])
        # rep index must be globally unique for this (comp,task); count ALL
        # recorded runs (any version) so a fresh campaign never reuses an id
        con = sqlite3.connect(DB_PATH)
        con.executescript(SCHEMA)
        rep = (con.execute("SELECT COUNT(*) FROM runs WHERE competitor=? "
                           "AND task=?", (comp["name"], t)).fetchone()[0]) + 1
        con.close()
        stable, rel = _is_stable(turns, args.nmin, args.tol)
        while not stable and len(turns) < args.nmax:
            if args.budget_usd and spent >= args.budget_usd:
                print(f"  budget exhausted (${spent:.2f}) — stopping")
                break
            r = run_one(comp, tasks[t], rep, args, cver)
            rep += 1
            spent += r.get("total_cost_usd") or 0.0
            if r["status"] == "ok" and r.get("num_turns") is not None:
                turns.append(r["num_turns"])
            stable, rel = _is_stable(turns, args.nmin, args.tol)
            import statistics as _st
            m = _st.mean(turns) if turns else 0
            print(f"  {t:<22} n={len(turns):>2} mean={m:>5.1f} "
                  f"rel_SEM={('%.3f' % rel) if rel is not None else '  -- '} "
                  f"{'STABLE' if stable else '':<7} "
                  f"last={r['status']}/{r.get('num_turns')} "
                  f"(${spent:.2f})", flush=True)
        import statistics as _st
        m = _st.mean(turns) if turns else 0
        summary.append((t, len(turns), m, rel, stable))
        print(f"  -> {t}: {'CONVERGED' if stable else 'NOT converged (cap)'} "
              f"n={len(turns)} mean={m:.1f}\n", flush=True)
    print("=== stabilization summary (control @ %s) ===" % cver)
    for t, n, m, rel, st in summary:
        print(f"  {t:<22} n={n:>2} mean_turns={m:>5.1f} "
              f"{'stable' if st else 'CAPPED'}")


def cmd_list(_args):
    print("tasks:")
    for t in load_tasks().values():
        print(f"  {t['id']:<20} {t['title']}")
    print("competitors:")
    for c in load_competitors().values():
        flag = "" if c.get("verified") else "  [unverified manifest]"
        print(f"  {c['name']:<20} {c.get('display_name', '')}{flag}")


def cmd_selftest(args):
    """Build every workspace and run every verifier against an empty answer.
    Each score must not exceed the task's declared baseline (the score an
    untouched workspace already earns, default 0) and no verifier may crash."""
    tasks = load_tasks()
    base = Path(CFG["runs_root"]) / "selftest"
    shutil.rmtree(base, ignore_errors=True)
    ok = True
    for t in tasks.values():
        ws = base / t["id"]
        build_workspace(t, ws)
        ans = ws / "_empty_answer.txt"
        ans.write_text("")
        try:
            score, out = run_verify(t, ws, ans)
        except Exception as e:
            print(f"  {t['id']:<20} CRASH {e}")
            ok = False
            continue
        baseline = t.get("baseline_score", 0.0)
        status = ("ok" if score <= baseline
                  else f"UNEXPECTED score={score} > baseline={baseline}")
        if score > baseline:
            ok = False
        print(f"  {t['id']:<20} {status}")
    shutil.rmtree(base, ignore_errors=True)
    print("selftest", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("selftest")
    # Pure analysis over the existing DB — reads only, runs no sessions.
    sub.add_parser("reconcile")
    for name in ("run", "calibrate", "smoke"):
        p = sub.add_parser(name)
        p.add_argument("-c", "--competitors",
                       default="control" if name != "run" else None,
                       required=(name == "run"))
        p.add_argument("-t", "--tasks",
                       default="doc-digest" if name == "smoke" else "all")
        p.add_argument("--reps", type=int,
                       default=1 if name == "smoke" else CFG["default_reps"])
        p.add_argument("--model", default=CFG["model"])
        p.add_argument("--budget-usd", type=float, default=None)
        p.add_argument("--allow-unverified", action="store_true")
        p.add_argument("--keep-workspaces", action="store_true")
        p.add_argument("--rerun", action="store_true",
                       help="ignore completed runs instead of resuming")
        p.add_argument("--skip-mcp-healthcheck", action="store_true",
                       help="skip the once-per-campaign MCP server "
                            "handshake preflight")
        p.add_argument("--max-consecutive-errors", type=int, default=5,
                       help="abort after this many consecutive claude_error "
                            "runs (expired credentials, API outage)")
    ps = sub.add_parser("stabilize",
                        help="run a competitor (default control) per task "
                             "until its mean num_turns stabilizes")
    ps.add_argument("-c", "--competitors", default="control")
    ps.add_argument("-t", "--tasks", default="all")
    ps.add_argument("--model", default=CFG["model"])
    ps.add_argument("--nmin", type=int, default=5,
                    help="minimum reps before declaring stability")
    ps.add_argument("--nmax", type=int, default=30,
                    help="hard cap on reps per task")
    ps.add_argument("--tol", type=float, default=0.05,
                    help="stop when relative SEM of the mean <= tol")
    ps.add_argument("--budget-usd", type=float, default=None)
    ps.add_argument("--keep-workspaces", action="store_true")
    ps.add_argument("--skip-mcp-healthcheck", action="store_true")
    args = ap.parse_args()
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "reconcile":
        sys.exit(1 if reconcile() else 0)
    elif args.cmd == "selftest":
        cmd_selftest(args)
    elif args.cmd == "stabilize":
        cmd_stabilize(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
