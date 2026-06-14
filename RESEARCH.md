# THOL research track — a learned, context-aware interception layer

## Why

THOL's headline result is that today's token optimizers don't reduce real
end-to-end cost, for two distinct reasons:

1. **Lossy compression.** Output-compaction hooks drop bytes that turn out to be
   needed, so the agent re-fetches them — more turns, more tokens (e.g. squeez
   4.2× control input on `log-needle-zh`).
2. **Adoption.** MCP/index tools are invoked in ~0–1 of 60 runs, so their
   standing schema overhead is paid for nothing — and when invoked, the call is
   often not the cost-minimizing choice.

Both are *decision* problems: **what to keep when compacting**, and **which
transform (if any) to apply in a given situation**. The bet of this track: those
decisions are learnable from agent trajectories, and the right place to act on
them is the **always-on hook**, not an MCP tool the agent must choose to call.

## Two decisions, kept separate

- **Compression policy** — given (tool output, command, session context), choose
  the keep/drop/summarize that minimizes delivered tokens *subject to* no
  downstream re-fetch. A per-span salience scorer.
- **Routing / silent substitution** — given the situation, decide whether to
  attach/transform context (e.g. auto-attach a structural summary to a `Read`)
  to lower expected end-to-end cost. A contextual policy.

### Where the model plugs in (the crux)

| Point | Verdict |
|-------|---------|
| **PostToolUse / PreToolUse hook** | ✅ 100% activation, sees every output + context, already where compactors live. Host the compression policy **and** silent substitution here. |
| MCP "meta-tool" the agent calls | ❌ inherits the adoption problem. |
| API proxy between agent and model | ⚠️ more powerful but not a sanctioned Claude Code integration point; hooks are. |
| CLAUDE.md / system-prompt steering | ⚠️ coarse, and itself a per-turn token rent. |

**Putting the decision in the hook dissolves the adoption problem** (hooks need
no adoption) and turns "a tool the agent may call" into "an automatic transform
the agent just benefits from." Keep tokenade's `expand_ref` as the exact-recovery
escape hatch: a wrong drop becomes cheap to undo (no re-execution), so a learned
*aggressive* compressor has a **bounded downside**.

## Data first: mine the trajectories into a labeled dataset

Before choosing a model, build the training set from the runs THOL already
produced (700+ full agent trajectories with outcomes). Labels come in two tiers.

### Tier 1 — compression labels (directly observable, no counterfactual)

For each tool **output** O at turn *i* of a run, scan turns *> i* to find which
of O's content is **actually used later** — referenced in the agent's reasoning,
quoted in the final answer, or re-fetched (re-`cat`/`grep`, `expand_ref`). Then:

- **needed-set(O)** = the spans of O that reappear downstream.
- **oracle keep-set(O)** = the minimal set of O's lines covering needed-set — the
  *ideal* compression for that output. `1 - |keep| / |O|` is the achievable
  compression at zero information loss.
- **re-fetch(O)** = did the agent later re-acquire something O contained? (the
  clean negative signal for a real compactor that dropped it).

**Control runs are the clean source**: outputs are full and uncompressed, so
needed-set is measured against the complete text. Competitor runs add the
real-world signal: did their actual compaction drop something that was re-fetched?

### Tier 2 — routing labels (partly counterfactual, scaffold for later)

"Was invoking tool X the right call at this round?" needs the counterfactual
(what the alternative action would have cost from this state). For now we only
have **task-level** marginals from paired control-vs-tool runs. Per-round routing
labels require future data collection: the **forced-adoption arm** and A/B at
decision points. The schema reserves fields for this; we don't fabricate it.

### Dataset schema (v0 — will evolve)

One JSONL record per decision point (tool output):

```
run_id, task, competitor, rep, turn_index, claude_version, model
tool_name, command            # the action that produced the output
output_tokens_raw             # size of the full output
output_tokens_delivered       # after the competitor's compaction (== raw for control)
compaction_applied            # none | hook:<name> | mcp:<name>
# --- Tier-1 labels ---
needed_line_idxs              # lines of the output referenced downstream
oracle_keep_ratio             # |needed lines| / |total lines|  (0 = drop all, 1 = keep all)
referenced_tokens             # salient tokens (ids/paths/numbers/hashes) reused later
refetched                     # bool: agent re-acquired content this output held
# --- context (for conditioning) ---
task_prompt_ref, prior_turns_digest   # pointers/hashes, not full text (kept out of the row)
# --- run outcome (for crediting) ---
run_success, run_cost_usd, run_num_turns
```

The headline target derived from this is **oracle_keep_ratio** vs what each
compactor actually delivered: the gap between "ideal lossless compression" and
"what squeez/tokenade did" is the learnable signal.

### Honest caveats on v1 labels

- "Referenced downstream" is detected by **token/line overlap** (identifiers,
  paths, numbers, hashes, verbatim lines) between an output and later
  commands/answers. This is a **recall-oriented heuristic**, not semantic ground
  truth — it will over-keep (safe) more than over-drop. Good enough to bootstrap;
  refine with embeddings / attribution later.
- Re-fetch detection is conservative (same file/resource re-touched after a
  compaction). Misses paraphrastic recovery.
- OOD warning baked in from THOL: non-Latin / unusual formats are where lossy
  compaction blew up — the dataset must keep these prominently so the model
  learns to be conservative there.

## Evaluation loop

THOL is the test harness for whatever model this produces: add it as
`competitors/learned-hook/` and measure end-to-end cost against the static
compactors, on the existing battery **plus** the planned long-session /
high-noise task (the regime where command-output compaction actually pays off —
see README "Limitations"). Train → evaluate → refine, closed by the harness.

## Status

- [x] Findings that motivate this (THOL campaign, 720 runs)
- [x] `research/build_dataset.py` — Tier-1 extractor from transcripts
- [x] First dataset (**9,069 decision points** over 1,217 trajectories). Headline:
      `oracle_keep_ratio` mean **0.53** / median 0.49 → **~47% of output lines are
      never referenced downstream**, and **~65% on large (≥30-line) outputs** — real
      lossless compression headroom. By producer: `Read` keeps 0.47, `Bash` 0.51,
      `Edit` 0.77.
- [x] **Refined re-fetch label** — two clean signals that net out normal
      re-reading: (a) *strong* = an explicit recovery call (`expand_ref` /
      `search_stash`) after a compacted output → tokenade **4%** of outputs;
      (b) *excess re-access vs control per task* → **rtk +5 pts, squeez +3 pts**
      (lossy compaction forcing re-access), tokenade ~+1, tok-hooksonly −1. The
      v1 (everything ~50%, control included) didn't discriminate; this does.
- [x] **Heuristic baselines vs oracle — the result that justifies a learned model.**
      B1 denoise: recall 0.99, **2%** compression. B2 salient: recall 0.96, **6%**.
      The oracle says **47% (65% on large outputs)** is losslessly droppable. Simple
      rules capture almost none of it, because the droppable lines are *real content
      that happens to go unused downstream* — only identifiable with task/context
      awareness. **The headroom is real AND out of reach of dumb rules → a
      context-aware learned compactor is warranted.**
- [x] **Scorer v1** (`research/train_scorer.py`, logistic regression, 18
      features, split by run). VAL **ROC-AUC 0.838**; at a threshold tuned on
      train for ≥0.95 recall of needed lines, it compresses **32%** on held-out
      runs — vs **6%** for the best heuristic and **47%** lossless oracle, i.e. it
      safely captures ~2/3 of the headroom that rules cannot. Top signals: drop
      decorative lines (−1.58), **keep lines overlapping the task prompt (+0.87 —
      context-conditioning is the #2 feature, exactly why context-free rules
      fail)**, keep salient/path-bearing content. Tiny + interpretable =
      hook-deployable.
- [ ] End-to-end eval: wire the scorer as `competitors/learned-hook/` and measure
      real session cost via THOL (does 32% line-compression convert to end-to-end
      savings without extra re-fetches?).
- [ ] Long-session / high-noise task for the eval battery
- [ ] Tier-2 routing data (forced-adoption arm / decision-point A/B)
- [ ] Stronger model + richer features (embeddings, cross-line context) once the
      LR baseline's end-to-end value is confirmed.
