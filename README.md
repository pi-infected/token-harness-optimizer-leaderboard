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

## Results (latest campaign)

Dataset: **720 runs** = 12 entries × 20 tasks × 3 repetitions, model
`claude-sonnet-4-6`, **single** Claude Code version `2.1.177`, fixtures seed-pinned,
generated 2026-06-13. Infrastructure-noise runs (transient API 401s during a
credential rotation, usage-policy false-positives) are excluded from scoring,
not silently dropped. Regenerate anytime with `python3 leaderboard.py`; every
raw per-run measurement lives in `docs/data/results.json`. All 20 task
verifiers pass `python3 runner.py selftest` (they award no credit on an
untouched workspace), so reported successes are earned, not an artifact of a
lenient grader.

End-to-end **cost per solved task, relative to control** (vanilla Claude Code).
Lower is better; **1.00 = no difference**. Control's median per-task
coefficient of variation (the noise floor) is **~7%** — differences smaller
than that are not real effects.

| # | optimizer | cost ratio | vs control | adoption | success |
|---|-----------|-----------|-----------|----------|---------|
| 1 | tok-mcponly | 1.01 | +1.1% | 3/60 | 60/60 |
| 2 | tok-hooksonly | 1.02 | +2.2% | 0/60 | 60/60 |
| 3 | claude-token-efficient | 1.03 | +2.6% | 0/60 | 60/60 |
| 4 | serena | 1.05 | +4.6% | 0/60 | 60/60 |
| 5 | lean-ctx | 1.06 | +6.0% | 1/60 | 60/60 |
| 6 | token-optimizer-mcp | 1.06 | +6.2% | 0/60 | 60/60 |
| 7 | tokenade (0.5.6) | 1.08 | +7.8% | 4/60 | 60/60 |
| 8 | rtk | 1.08 | +8.3% | 0/60 | 60/60 |
| 9 | code-review-graph | 1.09 | +9.1% | 0/60 | 60/60 |
| 10 | squeez | 1.10 | +10.4% | 0/60 | 60/60 |
| 11 | codegraph | 1.12 | +12.3% | 1/60 | 60/60 |

**Findings.**

1. **No optimizer reduces end-to-end session cost.** Every point estimate sits
   *at or above* control (+1.1% to +12.3%). With a 95% bootstrap CI on the
   aggregate ratio (resampling tasks **and** runs), **only `codegraph` is
   significantly more expensive** (CI `[1.04, 1.24]`, excludes 1.00); the other
   ten — tokenade included — are **statistically indistinguishable from doing
   nothing** (CIs straddle 1.00). Crucially, **none is significantly cheaper.**
   The per-row CI and a significance verdict are in [RESULTS.md](RESULTS.md).
2. **Two distinct failure modes — neither nets out.**
   - *MCP / index tools* (codegraph, lean-ctx, serena, token-optimizer-mcp,
     code-review-graph) are **adoption-gated**: the agent invoked them in only
     0–1 of 60 runs each, so their always-loaded tool schemas are paid every
     turn for nothing.
   - *Hook-based command-output compression* (rtk, squeez, tokenade's hooks)
     needs **no adoption** — the PostToolUse hook fires on every Bash/Read, and
     it does fire (transcripts show the compaction markers). But measured at the
     token level it does **not** net-reduce `input + cache_read` tokens, and for
     squeez/rtk it *inflates* them: lossy truncation drops the exact bytes a
     retrieval task needs, so the agent re-runs commands to recover them — more
     turns, more tokens (squeez reached **4.2× control** input on `log-needle-zh`,
     and +2–5 turns on `seo-audit`/`code-iterate-tests`). The always-on per-turn
     cost (injected CLAUDE.md/RTK.md, hook banners) is paid regardless. tokenade's
     hooks are the gentlest — they sometimes genuinely compress (−36% input and
     fewer turns on `code-feature-js`) — which is why `tok-hooksonly` lands
     closest to control, but its wins and overhead roughly cancel.
3. **Advertised compression rate ≠ real savings.** Tools headlining −58%,
   −90%, even −99% token reduction land between +1% and +12% on *whole-session*
   cost. That gap is the entire reason THOL measures end to end.
4. **When a tool *is* adopted on a fitting task, it can win big.** Example:
   on `code-migration-py` (a token-heavy refactor across 12 files) tokenade is
   triggered on all 3 reps and cuts cost to **0.37× (−63%), 95% CI [0.22, 0.84]**
   — a real, significant saving. The bottleneck is how rarely such triggering
   happens on everyday tasks.

**Per-task notes.** Adoption is concentrated: across all 11 × 20 = 220
(optimizer, task) cells, the agent actually invoked the tool in only **5**. The
two real wins are both on `code-migration-py` (a heavy multi-file refactor),
where the MCP tools are triggered on all 3 reps — **tokenade 0.37×** and
**tok-mcponly 0.40×**. Conversely, output-compaction hooks can *raise* cost on
retrieval tasks by hiding bytes the agent then re-fetches: **squeez 3.94×** on
`log-needle-zh` (verbatim needles in a noisy Chinese log) and **tok-hooksonly
1.80×** on `log-needle`. Most remaining cells sit within ±5% of control. Full
per-task ratios with 95% CIs are in [RESULTS.md](RESULTS.md) / `docs/data/results.json`.

**Scope & exclusions (for honesty).**

- **claude-context** — excluded from the ranking: it requires an `OPENAI_API_KEY`
  and a Milvus/Zilliz vector DB; verified that keyless its MCP server never
  exposes tools, so it would only measure vanilla Claude Code.
- **claude-mem** — excluded: it is a cross-session *memory* tool, fundamentally
  at odds with the per-run throwaway-HOME isolation (memory never persists
  between runs), so a single-session-cost benchmark can only measure its
  overhead, not its benefit. Documented rather than ranked.
- Figures are end-to-end USD, not isolated compression ratios. Early single-rep
  numbers were noisy; only the ≥3-rep figures above should be quoted.

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

## Limitations & future work

- **Adoption confound.** With near-zero adoption, the board mostly measures each
  tool's *standing overhead*, not its *capability when used*. A "+8%" can mean
  "the tool is useless" **or** "the agent never reached for it." A planned
  **forced-adoption arm** (a CLAUDE.md instruction that mandates the tool, or
  prompts engineered to invoke it) would separate the two — the
  `code-migration-py` result (−63% when tokenade *is* triggered) hints the
  capability is real and the bottleneck is triggering.
- **One model, one harness version.** Results are for `claude-sonnet-4-6` on
  Claude Code `2.1.177`. A smarter or cheaper model, or a future CC version,
  could shift both the overhead and the adoption rate. Re-running on more
  models is the obvious extension.
- **Finite, general task battery.** 20 tasks chosen to span everyday coding and
  non-coding work. A tool tuned for a workflow we don't cover (huge monorepos,
  long multi-session projects) could look better there.
- **Memory / external-service tools aren't covered.** Cross-session memory
  tools (claude-mem) can't show value under per-run isolation, and tools
  requiring paid external services (claude-context → OpenAI + Milvus) aren't
  provisioned. Both are documented exclusions, not measured.
- **Small per-task samples.** 3 reps per cell; noisy tasks have wide CIs. The
  aggregate CI is the reliable figure; single per-task ratios should be read
  with their interval.

## License & contributing

MIT (see [LICENSE](LICENSE)). Tool maintainers can correct their own entry —
see [CONTRIBUTING.md](CONTRIBUTING.md); manifest PRs are the only accepted way
to change how a tool is installed, which is what keeps the board impartial.
