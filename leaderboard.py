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
import random
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "results.sqlite"
BOOT = 10_000
SEED = 1234


def rows():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    # 'learned-hook' and 'tokenade-forced' are THIS repo's own research arms
    # (RESEARCH.md), not surveyed third-party tools — kept out of the public board.
    out = [dict(r) for r in con.execute(
        "SELECT * FROM runs WHERE status='ok' AND score IS NOT NULL "
        "AND competitor NOT IN ('learned-hook','tokenade-forced')")]
    bad = [dict(r) for r in con.execute(
        "SELECT competitor, task, status, COUNT(*) n FROM runs "
        "WHERE status!='ok' GROUP BY competitor, task, status")]
    con.close()
    return out, bad


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


def compute(ok, bad):
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
            per_task[t] = {
                "n": len(runs), "successes": len(succ),
                "mean_cost": (st.mean(costs) if costs else None),
                "ratio": ratio, "ci_lo": lo, "ci_hi": hi,
                "adoption": len(adopted), "mean_wall_s": wall,
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

    return {
        "params": {"bootstrap_draws": BOOT, "seed": SEED, "ci": "95%"},
        "model": sorted({r.get("model") for r in ok if r.get("model")}),
        "claude_versions": sorted({r["claude_version"] for r in ok}),
        "tasks": tasks,
        "control_noise_floor": noise,
        "competitors": competitors,
        "ranking": ranking,
        "non_ok": [{"competitor": b["competitor"], "task": b["task"],
                    "status": b["status"], "n": b["n"]} for b in bad],
    }


def render_md(d):
    L = ["# THOL leaderboard\n", ""]
    if len(d["claude_versions"]) > 1:
        L.append("> **WARNING — mixed Claude Code versions in the data: "
                 f"{d['claude_versions']}.** Session cost varies across "
                 "harness versions; ratios are only valid within a single "
                 "version. Re-run outdated rows before publishing.\n")

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
    ok, bad = rows()
    d = compute(ok, bad)
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
