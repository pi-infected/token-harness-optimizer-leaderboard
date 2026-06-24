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
   generated deterministically (`fixtures/generate_fixtures.py`, fixed seed) —
   verified byte-identical (same SHA-256 over `fixtures/out` + `fixtures/truth`)
   across regenerations, so anyone reproduces the exact same inputs + ground truth.
3. **Pre-registered tasks.** The task set is frozen before competitor runs and
   never edited to flatter or punish a specific tool. The only post-hoc filter is
   a stated, tool-blind rule: tasks where the control averages under ~5 turns are
   dropped — too trivial to separate any tool (everyone lands on the same
   near-zero cost), and unlike real agent work.
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

## Results

The live board is the source of truth: the long-session **headline ranking**, the
per-session-size **token bands**, the **generous-system-prompt** comparison and the
full **per-task detail** are all on the GitHub Pages site, generated from
`docs/data/results.json`. Reproduce every figure straight from the database with
`python3 reproduce_tables.py` (it prints the exact tables the site renders). A
plain-English summary is in **[What the benchmark says so far](#what-the-benchmark-says-so-far)**.

All figures are means over a competitor's successful runs; costs are aggregated as a
geometric mean of per-task ratios (a cost-weighted total agrees within a point).
Infrastructure-noise runs (transient API 401s, usage-policy false-positives) are
excluded from scoring, not silently dropped; verifiers award no credit on an
untouched workspace (`python3 runner.py selftest`), so successes are earned.

**Two tools are tracked but not ranked** (documented, not hidden):
- **claude-context** needs an `OPENAI_API_KEY` + a Milvus/Zilliz vector DB; keyless,
  its MCP server exposes no tools, so it would only measure vanilla Claude Code.
- **claude-mem** is a cross-session *memory* tool, at odds with the per-run
  throwaway-`HOME` isolation (memory never persists between runs), so a
  single-session-cost benchmark can only measure its overhead.

## Task battery (12 tasks)

Pre-registered and frozen before any competitor run; scored by programmatic
verifiers against ground truth that is never copied into the workspace. Trivially
-short tasks (control averaging under ~5 turns) are excluded by the stated rule
above. Fixtures are generated deterministically (`fixtures/*.py`, fixed seed);
`code-overview-cobra` runs against a pinned real repo (`repos.lock.json`).

| id | task | workspace | threshold |
|----|------|-----------|-----------|
| code-bugfix-py | fix failing tests in a small Python lib | tinyledger fixture | 1.0 |
| code-debug-cascade-py | debug a large red accounting suite (10 bugs) | cascade-debug fixture | 1.0 |
| code-debug-ledger-py | debug a red accounting test-suite (5 bugs) | ledger-debug fixture | 1.0 |
| code-debug-pipeline-py | debug a red sales-ETL pipeline (9 bugs) | pipeline-debug fixture | 1.0 |
| code-feature-js | implement a function from a written spec (JS) | jsfeature fixture | 1.0 |
| code-feature-validate-py | implement a validators module + wire into 8 handlers | validate-feature fixture | 1.0 |
| code-iterate-tests | fix many failing tests via a run-fix-rerun loop | iterledger fixture | 1.0 |
| code-migration-py | migrate a deprecated API across 12 modules | migration-py fixture | 1.0 |
| code-overview-cobra | write an architecture overview of a real repo | spf13/cobra @ pinned | 1.0 |
| log-needle-zh | recover 5 verbatim needles from a noisy 6k-line Chinese log | log-needle-zh fixture | 1.0 |
| report-pdf | analyze a CSV and produce a PDF report | sales-csv fixture | 1.0 |
| seo-audit | SEO audit of a website export, write a report | seo-site fixture | 1.0 |

The repository also carries generators and verifiers for further tasks not yet
run in the published campaign; the board grows in batches as token budget allows.

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

## Limitations & future work

- **Is it just low adoption?** Worry: with near-zero adoption the board might
  measure *standing overhead*, not *capability when used*. We tested raising
  adoption with a **generous per-tool system prompt** (the **+GSP** arms on the
  board, which teach the agent which function to call when). It mostly made cost
  *worse*, not better — the prompt is billed every turn and the tools still don't
  pay for themselves even when the agent uses them. So a low default adoption rate
  isn't simply a bug to fix; for several tools it's already near cost-optimal.
- **One model, one harness version.** Results are for `claude-sonnet-4-6` on
  Claude Code `2.1.183`. A smarter or cheaper model, or a future CC version,
  could shift both the overhead and the adoption rate. Re-running on more
  models is the obvious extension.
- **Finite, general task battery.** 12 substantive tasks (trivially-short ones,
  where control finishes in under ~5 turns, are excluded — see below). A tool
  tuned for a workflow we don't cover (huge monorepos, long multi-session
  projects) could look better there.
- **Memory / external-service tools aren't covered.** Cross-session memory
  tools (claude-mem) can't show value under per-run isolation, and tools
  requiring paid external services (claude-context → OpenAI + Milvus) aren't
  provisioned. Both are documented exclusions, not measured.
- **Small per-task samples.** ~10 reps per cell; noisy tasks have wide CIs. The
  aggregate CI is the reliable figure; single per-task ratios should be read
  with their interval.
- **Task regime ≠ a long real session (likely the biggest caveat).** The 12
  tasks are mostly short, single-objective, and not command-output-heavy. Real
  agent work is long, multi-turn, and *noisy* — repeated `git`/`npm`/test runs,
  large `diff`/log dumps, the same files re-read many times — which is exactly
  the regime where command-output compaction and read-dedup earn their keep. So
  the board probably **under-credits hook-based compactors**: it tests them off
  their home turf. (Anecdote, not data: across the long, command-heavy session
  that produced this repo, with tokenade's hooks live, they read as *mildly
  net-helpful* — noisy-command compaction and read-dedup saved tokens; the
  occasional truncated-read→`expand_ref` round-trip was cheap — the opposite of
  the +7.8% these same hooks score on the short benchmark tasks.) A
  **long-session / high-noise task class** (a multi-step debugging or migration
  *session*, not a one-shot task) is the most important missing piece, and the
  fairest next addition to the battery.

## What the benchmark says so far

Used as documented, today's optimizers mostly don't beat plain Claude Code end to
end — several make it more expensive. The bottleneck is **adoption**: the agent
doesn't call an optimizer's tools often enough to pay back their overhead. A verbose
"use this tool when…" system prompt *can* raise adoption for some tools, but cost
still goes up — the tools don't pay for themselves even when used, and the prompt is
billed every turn. Where any tool helps, it's on **long, expensive sessions** (see the
token-band split on the site), never on short ones — which is also why trivially-short
tasks (control < ~5 turns) are excluded. New tools are added as token budget allows.

## License & contributing

MIT (see [LICENSE](LICENSE)). Tool maintainers can correct their own entry —
see [CONTRIBUTING.md](CONTRIBUTING.md); manifest PRs are the only accepted way
to change how a tool is installed, which is what keeps the board impartial.
