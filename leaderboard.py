#!/usr/bin/env python3
"""THOL leaderboard — paired statistics against the control, bootstrap CIs.

Reads results.sqlite, writes leaderboard.md (printed too) and results.json
(machine-readable: aggregates + every raw measurement, for the web page and
independent re-analysis).

Methodology:
- per (competitor, task): success rate; mean cost over SUCCESSFUL runs;
  ratio vs control's mean successful cost; 95% CI on the ratio by
  bootstrap resampling of both samples (10k draws, fixed seed).
- aggregate: geometric mean of per-task cost ratios over tasks where both
  the competitor and the control have at least one success.
- the control's per-task coefficient of variation (CV) is the published
  noise floor: ratio deltas inside it are not real effects.
"""
import json
import math
import os
import random
import re
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "results.sqlite"
BOOT = 10_000
SEED = 1234


def active_tasks():
    """The benchmark scores ONLY tasks whose definition is present in tasks/.
    Trivially-short tasks — where vanilla Claude Code (control) finishes in
    under ~5 turns on average — were moved out of tasks/ (into a local,
    git-ignored folder): on those, every tool lands on the same near-zero cost,
    so only fixed overhead shows and nobody can win. They're also unlike real
    agent work. Moving the task dir out is what removes it here — single source
    of truth, no hard-coded exclusion list."""
    return {p.name for p in (ROOT / "tasks").iterdir()
            if p.is_dir() and (p / "task.json").exists()}


# Token-usage bands (control's TOTAL tokens for a task — input+output+cache),
# so the board can be read per cost regime: where do real sessions land?
TOKEN_BANDS = [(0, 200_000, "0–200k"),
               (200_000, 400_000, "200k–400k"),
               (400_000, 1_000_000, "400k–1M")]


def _vkey(v):
    """Sortable key for a claude_version string like '2.1.177 (Claude Code)'."""
    nums = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in nums[:3]) if nums else (0,)


def rows(campaign=None):
    """Read OK runs for ONE campaign (= one claude_version). Mixing harness
    versions is the contamination that biased earlier boards (2.1.170/172/173
    bleeding into a 2.1.177 ranking): session cost and turn counts shift with
    the harness, so a ratio is only meaningful within a single version.

    campaign: explicit claude_version (or substring like '2.1.177'); falls back
    to env THOL_CAMPAIGN; otherwise the LATEST version present in the DB."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    versions = [r[0] for r in con.execute(
        "SELECT DISTINCT claude_version FROM runs WHERE status='ok' "
        "AND claude_version IS NOT NULL")]
    campaign = campaign or os.environ.get("THOL_CAMPAIGN")
    if campaign:
        match = [v for v in versions if campaign in (v or "")]
        campaign = match[0] if match else campaign
    elif versions:
        campaign = max(versions, key=_vkey)
    # Filters:
    #  * tasks — only those still present in tasks/ (see active_tasks): the
    #    trivially-short tasks (control < ~5 turns) were moved out, which
    #    removes them from every aggregate here.
    #  * '*-gsp' arms — the "generous system prompt" experiment (a verbose
    #    per-tool prompt teaching the agent which CLI/MCP function to use when).
    #    It made costs WORSE (overhead, ~no extra adoption), so it's reported in
    #    the methodology, not mixed into the headline tool ranking.
    #  * 'learned-hook' / 'tokenade-forced' — defensive exclusion of legacy
    #    internal experiment arms, should they ever reappear in a results DB.
    keep = active_tasks()
    out = [dict(r) for r in con.execute(
        "SELECT * FROM runs WHERE status='ok' AND score IS NOT NULL "
        "AND claude_version=? "
        "AND competitor NOT IN ('learned-hook','tokenade-forced') "
        "AND competitor NOT LIKE '%-gsp'",
        (campaign,)) if r["task"] in keep]
    bad = [dict(r) for r in con.execute(
        "SELECT competitor, task, status, COUNT(*) n FROM runs "
        "WHERE status!='ok' AND claude_version=? "
        "GROUP BY competitor, task, status", (campaign,))]
    # The '*-gsp' arms (generous system prompt) — kept separate so the GSP
    # comparison table can show that the verbose prompt raised cost.
    gsp = [dict(r) for r in con.execute(
        "SELECT * FROM runs WHERE status='ok' AND score IS NOT NULL "
        "AND claude_version=? AND competitor LIKE '%-gsp'",
        (campaign,)) if r["task"] in keep]
    con.close()
    return out, gsp, bad, campaign


def boot_ratio(comp_costs, ctrl_costs, rng):
    draws = []
    for _ in range(BOOT):
        a = [rng.choice(comp_costs) for _ in comp_costs]
        b = [rng.choice(ctrl_costs) for _ in ctrl_costs]
        mb = st.mean(b)
        if mb > 0:
            draws.append(st.mean(a) / mb)
    draws.sort()
    return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]


def boot_aggregate(pairs, rng):
    """95% CI on the AGGREGATE geometric-mean cost ratio. Each draw resamples
    tasks (with replacement) and, within each, the competitor's and control's
    successful-run costs — so both the across-task and within-task variance feed
    the interval. A tool whose interval excludes 1.00 differs significantly from
    control overall; one that straddles 1.00 is within the noise."""
    if not pairs:
        return None, None
    n = len(pairs)
    draws = []
    for _ in range(BOOT):
        logs = []
        for _ in range(n):
            comp_costs, ctrl_costs = rng.choice(pairs)
            a = st.mean([rng.choice(comp_costs) for _ in comp_costs])
            b = st.mean([rng.choice(ctrl_costs) for _ in ctrl_costs])
            if a > 0 and b > 0:
                logs.append(math.log(a / b))
        if logs:
            draws.append(math.exp(st.mean(logs)))
    draws.sort()
    return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]


def compute(ok, gsp, bad):
    """Single source of truth: returns a structured dict consumed by both the
    markdown renderer and the JSON export. The RNG is advanced in a fixed
    order (competitors sorted, tasks sorted) so results are reproducible."""
    by = defaultdict(list)
    for r in ok:
        by[(r["competitor"], r["task"])].append(r)
    tasks = sorted({t for _, t in by})
    comps = sorted({c for c, _ in by})
    if "control" not in comps:
        sys.exit("no control runs — run `runner.py calibrate` first")
    rng = random.Random(SEED)

    # ---- control noise floor + raw successful costs per task
    ctrl_succ_costs = {}
    noise = {}
    for t in tasks:
        runs = by.get(("control", t), [])
        succ = [r for r in runs if r["success"]]
        costs = [r["total_cost_usd"] for r in succ
                 if r["total_cost_usd"] is not None]
        ctrl_succ_costs[t] = costs
        cv = (st.stdev(costs) / st.mean(costs)
              if len(costs) >= 2 and st.mean(costs) > 0 else None)
        noise[t] = {"n": len(runs), "successes": len(succ),
                    "mean_cost": (st.mean(costs) if costs else None),
                    "cv": cv, "costs": costs}

    competitors = {}
    summary = []
    for c in comps:
        if c == "control":
            continue
        cver = next((r.get("competitor_version") for r in ok
                     if r["competitor"] == c and r.get("competitor_version")),
                    None)
        per_task = {}
        ratios = []
        compared_pairs = []
        n_runs = n_succ = 0
        for t in tasks:
            runs = by.get((c, t), [])
            if not runs:
                continue
            n_runs += len(runs)
            succ = [r for r in runs if r["success"]]
            n_succ += len(succ)
            costs = [r["total_cost_usd"] for r in succ
                     if r["total_cost_usd"] is not None]
            adopted = [r for r in runs if (r["competitor_tool_calls"] or 0) > 0]
            wall = st.mean([r["wall_ms"] / 1000 for r in runs])
            ratio = lo = hi = None
            if costs and ctrl_succ_costs.get(t):
                ratio = st.mean(costs) / st.mean(ctrl_succ_costs[t])
                lo, hi = boot_ratio(costs, ctrl_succ_costs[t], rng)
                ratios.append(ratio)
                compared_pairs.append((costs, ctrl_succ_costs[t]))
            tok = lambda k: (st.mean([r[k] or 0 for r in runs]) if runs else 0)
            per_task[t] = {
                "n": len(runs), "successes": len(succ),
                "mean_cost": (st.mean(costs) if costs else None),
                "ratio": ratio, "ci_lo": lo, "ci_hi": hi,
                "adoption": len(adopted), "mean_wall_s": wall,
                # Token breakdown, labelled for a lay reader (Anthropic's cache
                # accounting under the hood): "input token" = cache_creation
                # (the new input actually processed), "output token" = output,
                # "cache token" = cache_read (input reused from cache).
                "mean_input_tokens": round(tok("cache_creation_tokens")),
                "mean_output_tokens": round(tok("output_tokens")),
                "mean_cache_tokens": round(tok("cache_read_tokens")),
                # raw measurements for full transparency / re-analysis
                "costs": costs,
                "scores": [r["score"] for r in runs],
                "tool_calls": [r["tool_calls"] for r in runs],
                "competitor_tool_calls": [r["competitor_tool_calls"] for r in runs],
            }
        agg = (math.exp(st.mean(list(map(math.log, ratios))))
               if ratios else None)
        agg_lo, agg_hi = boot_aggregate(compared_pairs, rng)
        competitors[c] = {
            "version": cver, "aggregate_cost_ratio": agg,
            "aggregate_ci_lo": agg_lo, "aggregate_ci_hi": agg_hi,
            "n_success": n_succ, "n_runs": n_runs,
            "tasks_compared": len(ratios), "per_task": per_task,
        }
        summary.append((c, agg, agg_lo, agg_hi, n_succ, n_runs, len(ratios)))

    ranked = sorted([s for s in summary if s[1] is not None],
                    key=lambda s: s[1])
    ranking = [{"rank": i, "competitor": c, "aggregate_cost_ratio": agg,
                "aggregate_ci_lo": lo, "aggregate_ci_hi": hi,
                "n_success": ns, "n_runs": nr, "tasks_compared": nt}
               for i, (c, agg, lo, hi, ns, nr, nt) in enumerate(ranked, 1)]
    ranking += [{"rank": None, "competitor": c,
                 "aggregate_cost_ratio": None, "aggregate_ci_lo": None,
                 "aggregate_ci_hi": None, "n_success": ns,
                 "n_runs": nr, "tasks_compared": 0}
                for c, agg, lo, hi, ns, nr, nt in summary if agg is None]

    # ---- token-usage bands: group tasks by how many TOTAL tokens vanilla
    # Claude Code (control) burns on them, so the board can be read per cost
    # regime (where do real sessions actually land?). Total = input + output +
    # cache_creation + cache_read, averaged over control's runs of that task.
    def ctrl_tokens(t):
        rs = [r for r in by.get(("control", t), [])]
        vals = [(r["input_tokens"] or 0) + (r["output_tokens"] or 0)
                + (r["cache_creation_tokens"] or 0) + (r["cache_read_tokens"] or 0)
                for r in rs]
        return st.mean(vals) if vals else 0
    task_tokens = {t: ctrl_tokens(t) for t in tasks}

    # mean input / output / cache tokens for ANY competitor (control included)
    # over a set of tasks — averages the per-task means so tasks weigh equally.
    def mean_tokens(comp, task_list, src=by):
        # "input" = cache_creation (new input processed), "output" = output,
        # "cache" = cache_read (input reused from cache). See per_task above.
        ins, outs, cas = [], [], []
        for t in task_list:
            rs = src.get((comp, t), [])
            if not rs:
                continue
            ins.append(st.mean([r["cache_creation_tokens"] or 0 for r in rs]))
            outs.append(st.mean([r["output_tokens"] or 0 for r in rs]))
            cas.append(st.mean([r["cache_read_tokens"] or 0 for r in rs]))
        return {"input": round(st.mean(ins)) if ins else 0,
                "output": round(st.mean(outs)) if outs else 0,
                "cache": round(st.mean(cas)) if cas else 0}

    bands = []
    for lo_b, hi_b, label in TOKEN_BANDS:
        bt = sorted(t for t in tasks if lo_b <= task_tokens[t] < hi_b)
        rank = []
        # control first — the baseline (0% reduction) + its absolute token cost.
        if any(by.get(("control", t)) for t in bt):
            rank.append({"competitor": "control", "aggregate_cost_ratio": 1.0,
                         "tasks_compared": len([t for t in bt if by.get(("control", t))]),
                         "tokens": mean_tokens("control", bt)})
        for c, cd in competitors.items():
            rs = [cd["per_task"][t]["ratio"] for t in bt
                  if t in cd["per_task"] and cd["per_task"][t].get("ratio")]
            if rs:
                rank.append({"competitor": c,
                             "aggregate_cost_ratio": math.exp(st.mean(list(map(math.log, rs)))),
                             "tasks_compared": len(rs),
                             "tokens": mean_tokens(c, bt)})
        # cheapest-first; control (ratio 1.0 = 0% reduction) sorts into place
        # at the zero line, so the reader sees who actually beats the baseline.
        rank.sort(key=lambda e: e["aggregate_cost_ratio"])
        bands.append({"label": label, "lo": lo_b, "hi": hi_b,
                      "tasks": bt, "n_tasks": len(bt), "ranking": rank})

    # ---- HEADLINE ranking: long sessions only (control > 200k tokens). Most
    # real agent work is long, so this is the representative figure; reported as
    # a plain "cost reduction %" (= 100·(1 − ratio)) for a non-technical reader.
    HEADLINE_MIN = 200_000
    big = sorted(t for t in tasks if task_tokens[t] >= HEADLINE_MIN)
    headline = []
    for c, cd in competitors.items():
        rs = [cd["per_task"][t]["ratio"] for t in big
              if t in cd["per_task"] and cd["per_task"][t].get("ratio")]
        pairs_big = [(cd["per_task"][t]["costs"], ctrl_succ_costs[t]) for t in big
                     if t in cd["per_task"] and cd["per_task"][t]["costs"] and ctrl_succ_costs.get(t)]
        if not rs:
            continue
        ratio = math.exp(st.mean(list(map(math.log, rs))))
        lo, hi = boot_aggregate(pairs_big, rng)
        adopt = sum(cd["per_task"][t]["adoption"] for t in big if t in cd["per_task"])
        nrun = sum(cd["per_task"][t]["n"] for t in big if t in cd["per_task"])
        headline.append({
            "competitor": c, "cost_ratio": ratio,
            "cost_reduction_pct": round((1 - ratio) * 100, 1),
            "ci_lo_pct": (round((1 - hi) * 100, 1) if hi is not None else None),
            "ci_hi_pct": (round((1 - lo) * 100, 1) if lo is not None else None),
            "adoption": adopt, "n_runs": nrun, "tasks_compared": len(rs),
            "tokens": mean_tokens(c, big),
        })
    # control row — the baseline (0% reduction), sorted in at the zero line.
    if any(by.get(("control", t)) for t in big):
        headline.append({
            "competitor": "control", "cost_ratio": 1.0, "cost_reduction_pct": 0.0,
            "ci_lo_pct": None, "ci_hi_pct": None, "adoption": None,
            "n_runs": sum(len(by.get(("control", t), [])) for t in big),
            "tasks_compared": len([t for t in big if by.get(("control", t))]),
            "tokens": mean_tokens("control", big),
        })
    headline.sort(key=lambda e: e["cost_ratio"])

    # ---- GSP comparison: same headline computation, but for the "+GSP"
    # (generous system prompt) arms, with the delta vs the same tool WITHOUT
    # the prompt. Shows that the verbose prompt raised cost. base→headline%.
    by_gsp = defaultdict(list)
    for r in gsp:
        by_gsp[(r["competitor"], r["task"])].append(r)
    base_red = {e["competitor"]: e["cost_reduction_pct"] for e in headline}
    headline_gsp = []
    for gc in sorted({c for c, _ in by_gsp}):
        base = gc[:-4] if gc.endswith("-gsp") else gc
        rs, nrun, adopt = [], 0, 0
        for t in big:
            gr = by_gsp.get((gc, t), [])
            gcosts = [r["total_cost_usd"] for r in gr
                      if r["success"] and r["total_cost_usd"] is not None]
            nrun += len(gr)
            adopt += sum(1 for r in gr if (r["competitor_tool_calls"] or 0) > 0)
            if gcosts and ctrl_succ_costs.get(t):
                rs.append(st.mean(gcosts) / st.mean(ctrl_succ_costs[t]))
        if not rs:
            continue
        red = round((1 - math.exp(st.mean(list(map(math.log, rs))))) * 100, 1)
        headline_gsp.append({
            "competitor": gc, "base": base,
            "cost_reduction_pct": red,
            # delta in percentage points vs the same tool without GSP (None if
            # the base tool wasn't comparable on these long tasks)
            "delta_vs_base_pp": (round(red - base_red[base], 1) if base in base_red else None),
            "adoption": adopt, "n_runs": nrun, "tasks_compared": len(rs),
            "tokens": mean_tokens(gc, big, by_gsp),
        })
    headline_gsp.sort(key=lambda e: -e["cost_reduction_pct"])

    return {
        "params": {"bootstrap_draws": BOOT, "seed": SEED, "ci": "95%"},
        "model": sorted({r.get("model") for r in ok if r.get("model")}),
        "claude_versions": sorted({r["claude_version"] for r in ok}),
        "tasks": tasks,
        "task_control_tokens": {t: round(task_tokens[t]) for t in tasks},
        "headline_min_tokens": HEADLINE_MIN,
        "headline_n_tasks": len(big),
        "headline": headline,
        "headline_gsp": headline_gsp,
        "token_bands": bands,
        # control's per-task token breakdown (the baseline shown in the detail)
        "control_per_task": {t: {
            "n": len(by.get(("control", t), [])),
            "mean_input_tokens": mean_tokens("control", [t])["input"],
            "mean_output_tokens": mean_tokens("control", [t])["output"],
            "mean_cache_tokens": mean_tokens("control", [t])["cache"],
        } for t in tasks if by.get(("control", t))},
        "control_noise_floor": noise,
        "competitors": competitors,
        "ranking": ranking,
        "non_ok": [{"competitor": b["competitor"], "task": b["task"],
                    "status": b["status"], "n": b["n"]} for b in bad],
    }


def render_md(d):
    L = ["# THOL leaderboard\n", ""]
    L.append(f"> Campaign: **{d.get('campaign')}** — all rows below are scoped "
             "to this single Claude Code version (set `THOL_CAMPAIGN` to pick "
             "another). Ratios are only comparable within one harness version.\n")
    if len(d["claude_versions"]) > 1:
        L.append("> **WARNING — more than one Claude Code version slipped past "
                 f"the campaign filter: {d['claude_versions']}.** This should "
                 "not happen; investigate before publishing.\n")

    # ---- ranking (inserted at top after title)
    rank_lines = ["## Ranking (geometric mean cost ratio vs control, "
                  "successful runs only — lower is better)\n",
                  "| rank | competitor | agg. cost ratio [95% CI] | "
                  "vs control | success |", "|---|---|---|---|---|"]
    for e in d["ranking"]:
        if e["rank"] is not None:
            lo, hi = e.get("aggregate_ci_lo"), e.get("aggregate_ci_hi")
            ci = f" [{lo:.2f}, {hi:.2f}]" if lo is not None else ""
            if lo is not None and lo > 1:
                verdict = "more expensive (sig.)"
            elif hi is not None and hi < 1:
                verdict = "cheaper (sig.)"
            else:
                verdict = "≈ control (n.s.)"
            rank_lines.append(
                f"| {e['rank']} | {e['competitor']} | "
                f"**{e['aggregate_cost_ratio']:.2f}**{ci} | {verdict} | "
                f"{e['n_success']}/{e['n_runs']} |")
        else:
            rank_lines.append(
                f"| — | {e['competitor']} | no comparable successes | — | "
                f"{e['n_success']}/{e['n_runs']} |")
    L[1:1] = rank_lines

    # ---- control noise floor
    L.append("## Control (vanilla Claude Code) noise floor\n")
    L.append("| task | n | success | mean cost (succ.) | CV |")
    L.append("|---|---|---|---|---|")
    for t in d["tasks"]:
        nf = d["control_noise_floor"][t]
        L.append(f"| {t} | {nf['n']} | {nf['successes']}/{nf['n']} | "
                 f"{'$%.3f' % nf['mean_cost'] if nf['mean_cost'] is not None else '—'} | "
                 f"{'%.0f%%' % (nf['cv'] * 100) if nf['cv'] is not None else '—'} |")

    # ---- per-competitor
    for c, cd in d["competitors"].items():
        cver = cd["version"]
        L.append(f"\n## {c}{f' (version {cver})' if cver else ''}\n")
        L.append("| task | n | success | mean cost (succ.) | "
                 "cost ratio vs control [95% CI] | adoption | mean wall |")
        L.append("|---|---|---|---|---|---|---|")
        for t in d["tasks"]:
            pt = cd["per_task"].get(t)
            if not pt:
                continue
            ratio_txt = ("—" if pt["ratio"] is None
                         else f"{pt['ratio']:.2f} [{pt['ci_lo']:.2f}, "
                              f"{pt['ci_hi']:.2f}]")
            L.append(f"| {t} | {pt['n']} | {pt['successes']}/{pt['n']} | "
                     f"{'$%.3f' % pt['mean_cost'] if pt['mean_cost'] is not None else '—'} | "
                     f"{ratio_txt} | {pt['adoption']}/{pt['n']} | "
                     f"{pt['mean_wall_s']:.0f}s |")

    if d["non_ok"]:
        L.append("\n## Non-ok runs (timeouts, install failures…)\n")
        L.append("| competitor | task | status | n |")
        L.append("|---|---|---|---|")
        for b in d["non_ok"]:
            L.append(f"| {b['competitor']} | {b['task']} | {b['status']} | "
                     f"{b['n']} |")
    return "\n".join(L) + "\n"


def main():
    if not DB.exists():
        sys.exit("no results.sqlite yet — run runner.py first")
    ok, gsp, bad, campaign = rows()
    if not ok:
        sys.exit(f"no OK runs for campaign {campaign!r} — check THOL_CAMPAIGN")
    d = compute(ok, gsp, bad)
    d["campaign"] = campaign
    md = render_md(d)
    (ROOT / "leaderboard.md").write_text(md)
    payload = json.dumps(d, indent=1)
    (ROOT / "results.json").write_text(payload)
    # also publish into the GitHub Pages tree (committed, since the sqlite DB
    # is gitignored — results.json is the published dataset of record)
    site_data = ROOT / "docs" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    (site_data / "results.json").write_text(payload)
    print(md)


if __name__ == "__main__":
    main()
