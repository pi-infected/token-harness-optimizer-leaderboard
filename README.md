# THOL — Token-Harness Optimizer Leaderboard

An open, reproducible, **end-to-end** benchmark for tools that claim to reduce
the token consumption of coding agents (Claude Code harness optimizers:
MCP servers, output-compaction hooks, context indexes, CLI wrappers…).

## Why this exists

Every optimizer advertises a compression rate ("−58% tokens!", "−90%!").
Compression rate is the wrong metric. It does not tell you:

1. whether the agent **actually invokes** the tool during a real task,
2. whether the compacted output carries **enough signal** that the agent does
   not have to make extra calls to recover what was dropped,
3. what happens to the **end-to-end** session cost, including the permanent
   overhead the tool itself adds (MCP tool schemas re-sent every turn, hook
   banners, CLAUDE.md rules),
4. whether the task still **succeeds**.

THOL measures the only numbers that matter: **did the task succeed, what did
the full session cost, and how long did it take** — for the same task, same
model, same repo, with and without each optimizer.

## What a run is

One run = one fresh, fully isolated headless Claude Code session:

```
claude -p "<task prompt>" --output-format stream-json --verbose \
       --model <pinned> --max-turns <cap> --dangerously-skip-permissions \
       --strict-mcp-config [--mcp-config <competitor's servers only>]
```

- **Isolation.** Each run gets a full throwaway `HOME` (with
  `CLAUDE_CONFIG_DIR` at `<home>/.claude` inside it) and a throwaway
  workspace under `/tmp`, so: the host machine's settings, hooks, memory and
  MCP servers do not exist for the session; no ancestor `CLAUDE.md` leaks
  into context; and competitor installers or hooks that hardcode `~/.claude`
  (several do — e.g. squeez writes its persona block to `$HOME/.claude/CLAUDE.md`
  unconditionally) land in the sandbox, never on the host, while still being
  visible to the benchmarked session. Official installers (`squeez setup`,
  `rtk init -g`, `codegraph init`…) run per-run inside that sandbox and their
  duration is recorded as `setup_ms`. `--strict-mcp-config` guarantees only
  the competitor's declared servers are loaded. The host setup is never modified.
- **Installation fidelity.** Each competitor is installed exactly as its own
  README instructs, encoded in `competitors/<name>/manifest.json` with a
  pointer to the upstream doc that was followed. Maintainers can PR a fix to
  their manifest; that is the only accepted route to change how a tool is set
  up.
- **Measurement.** From the session's final `result` event we record
  `total_cost_usd`, the full token breakdown (fresh input / output / cache
  creation / cache reads — they have very different prices, which is why raw
  "total tokens" headlines mislead), `num_turns`, `duration_ms`. From the
  stream we record every tool call, which gives the **adoption rate**: did the
  agent use the optimizer's tools at all, and how often.
- **Verification.** Every task ships a programmatic verifier (`verify.py`)
  that scores the outcome 0–1 from ground truth that is *never present in the
  workspace*. No LLM judging on the scored path.

## Scoring

The headline ranking metric is **cost per solved task** relative to control
(vanilla Claude Code, same model, same prompts):

```
ratio(competitor, task) = mean cost of successful runs / mean control cost of successful runs
aggregate = geometric mean of ratios across tasks
```

with 95% bootstrap confidence intervals, plus, reported separately:
success rate, wall-clock time, adoption rate, and setup/indexing cost.
A tool that makes sessions cheap by making them fail does not win:
failed runs never count as savings.

## Statistical protocol

1. **Calibrate first.** The control is run N times per task to measure its
   own variance (agent sampling is the dominant noise source). The control's
   coefficient of variation is published with the leaderboard; no competitor
   delta smaller than the control noise floor is presented as a real effect.
2. **Fixed everything else.** Model ID, Claude Code version, repo commits
   (`repos.lock.json`), task prompts and fixtures are pinned. Fixtures are
   generated deterministically (`fixtures/generate_fixtures.py`, fixed seed).
3. **Pre-registered tasks.** The task set is frozen before competitor runs;
   tasks are never added/removed to flatter or punish a specific tool.
4. **Everything published.** Full per-run transcripts, raw results DB, all
   manifests, all verifiers. Anyone can re-run the entire board.

## Impartiality charter

This benchmark is maintained by the author of one of the measured tools
(tokenade). That conflict of interest is handled by construction, not by
trust:

- the harness cannot tell competitors apart — every tool goes through the
  same manifest → isolated session → verifier pipeline;
- install steps follow each tool's own documentation, linked in its manifest,
  and upstream maintainers' corrections are accepted via PR;
- verifiers are frozen before any competitor run and check task outcomes,
  not tool behavior;
- all raw data (including runs unfavorable to any tool, tokenade included)
  is published unedited;
- the control (no optimizer) is a first-class competitor and its variance
  bounds every claim.

## Task battery (20 tasks, 7 code / 13 non-code)

Pre-registered and frozen before any competitor run. Most tasks are scored
pass/fail (threshold `1.0`); some allow partial credit (threshold shown)
where the outcome is graded — coverage, fraction of planted issues found,
editorial constraints. Ground truth lives in `fixtures/truth/` and is never
copied into a workspace. The multilingual variants (`-fr`, `-zh`) probe
whether output compactors mangle non-Latin / UTF-8 text.

### Code (7)

| id | task | workspace | scored on | thr |
|----|------|-----------|-----------|-----|
| code-bugfix-py | fix failing tests in a small Python lib | tinyledger fixture | unittest suite passes, tests untouched | 1.0 |
| code-feature-js | implement a function from a written spec (JS) | jsfeature fixture | hidden test file (not in workspace) | 1.0 |
| code-iterate-tests | fix many failing tests via a run-fix-rerun loop | iterledger fixture | full suite passes | 1.0 |
| code-migration-py | migrate a deprecated API across 12 modules | migration-py fixture | zero legacy imports + suite passes | 1.0 |
| code-qa-click | locate & explain a mechanism in a real repo | pallets/click @ pinned | answer names the right file + symbols | 1.0 |
| code-overview-cobra | write an architecture overview of a real repo | spf13/cobra @ pinned | references real files, coverage | 0.8 |
| code-debug-cilog | root-cause a CI failure from a noisy log | ci-log fixture | answer contains the planted cause | 1.0 |

### Non-code (13)

| id | task | workspace | scored on | thr |
|----|------|-----------|-----------|-----|
| config-peek | read two values from a tiny config file | tiny-config fixture | exact values (cheap-task control) | 1.0 |
| doc-digest | factual questions about a long internal doc | longdoc fixture | planted-fact markers | 1.0 |
| doc-digest-fr | same, French / UTF-8 document | longdoc-fr fixture | planted-fact markers | 1.0 |
| doc-digest-zh | same, Chinese (Han) / UTF-8 document | longdoc-zh fixture | planted-fact markers | 1.0 |
| data-analysis | aggregate questions over a 2k-row CSV | sales-csv fixture | exact values (rounding-tolerant) | 1.0 |
| data-bigvolume | aggregate questions over a 150k-row CSV | events-csv fixture | exact values | 1.0 |
| log-forensics | precise questions about a 5k-line access log | access-log fixture | exact counts/values | 1.0 |
| log-needle | recover 5 verbatim needles from a 6k-line log | release-log fixture | fraction of needles recovered | 0.8 |
| log-needle-zh | same, noisy 6k-line Chinese release log | log-needle-zh fixture | fraction of needles recovered | 0.8 |
| html-extract | extract facts from noisy HTML pages | html-docs fixture | fraction of facts correct | 0.8 |
| seo-audit | SEO audit of a website export, write a report | seo-site fixture | fraction of planted issues found | 0.7 |
| report-pdf | analyze a CSV and produce a PDF report | sales-csv fixture | valid PDF + correct key figures | 0.8 |
| writing-brief | write a post under hard editorial constraints | none | word count, sections, keywords, FAQ | 0.85 |

## Usage

```bash
bash setup/install_competitors.sh              # global tool binaries (one-time)
python3 fixtures/generate_fixtures.py          # one-time, deterministic
python3 runner.py list                          # tasks & competitors
python3 runner.py selftest                      # verifiers sane on empty workspaces
python3 runner.py calibrate --reps 10           # control variance, all tasks
python3 runner.py run -c rtk -t code-qa-click --reps 5
python3 runner.py run -c all -t all --reps 5    # full board
python3 leaderboard.py                          # stats + leaderboard.md
```

Requirements: Claude Code CLI (logged in, or `ANTHROPIC_API_KEY` set),
Python ≥ 3.10, Node ≥ 18 (two tasks), `pdftotext` (optional, one verifier
falls back without it).

Costs real API/subscription usage. `runner.py` prints a cost estimate and
running total; `--budget-usd` aborts the campaign when exceeded.

### Pause / resume

Every run is atomic: its row is written to `results.sqlite` only on
completion, and all state lives in the project directory (workspaces under
`/tmp` are disposable). So:

- **pause**: Ctrl-C (or kill the process) at any time;
- **resume**: relaunch the exact same command — completed
  (competitor, task, rep) triples are skipped, only missing runs execute;
- power loss / reboot: same as pause; an interrupted in-flight run left no
  row and is simply redone;
- `--rerun` ignores existing rows and redoes everything.

The Claude Code version is recorded per run; a publishable campaign should
run on a single version (check with `SELECT DISTINCT claude_version FROM runs`).
