#!/usr/bin/env python3
"""Print, straight from results.sqlite, the EXACT tables rendered on the THOL
site (docs/index.html) — same numbers, same columns, same formatting.

Purpose: zero ambiguity. Every figure on the web page is produced by
leaderboard.compute() and published to docs/data/results.json; this script
reads that same structure and lays it out as the page does, so anyone can
verify or reproduce each table from the raw database with one command:

    python3 reproduce_tables.py

Column → source mapping (all means are over a competitor's successful runs):
  cost reduction = 100 · (1 − geomean(per-task cost ratio vs control))
  adoption       = #runs where the agent actually called the tool / #runs
  input token    = mean cache_creation_tokens   (new input actually processed)
  output token   = mean output_tokens
  cache token    = mean cache_read_tokens        (input reused from cache)
  runs           = repetitions of that (tool, task) cell
Tasks included: only those in tasks/ (trivially-short tasks — control < ~5
turns on average — are excluded). Headline = tasks where control burns
> 200k total tokens.
"""
from leaderboard import rows, compute


def pct(x):
    if x is None:
        return "—"
    return ("+" if x >= 0 else "−") + f"{abs(x):.2f}%"


def ktok(n):
    if n is None:
        return "—"
    if n >= 1e6:
        return f"{n/1e6:.2f}M"
    if n >= 1e3:
        return f"{n/1e3:.2f}k"
    return str(n)


def red_of_ratio(r):
    return None if r is None else (1 - r) * 100


def row(cells, widths):
    return "  ".join(str(c).rjust(w) if i else str(c).ljust(w)
                     for i, (c, w) in enumerate(zip(cells, widths)))


def main():
    ok, gsp, bad, campaign = rows()
    d = compute(ok, gsp, bad)
    print(f"Campaign: {campaign}   model: {', '.join(d['model'])}")
    print(f"Tasks scored: {len(d['tasks'])}   (headline = {d['headline_n_tasks']} "
          f"tasks where control > {d['headline_min_tokens']:,} tokens)\n")

    # ---- HEADLINE (the first table on the page) ----
    print(f"== HEADLINE — cost reduction on long sessions (> {d['headline_min_tokens']:,} tokens) ==")
    W = [3, 24, 16, 12, 12, 12, 12]
    print(row(["#", "optimizer", "cost reduction", "adoption", "input tok", "output tok", "cache tok"], W))
    for i, e in enumerate(d["headline"], 1):
        t = e.get("tokens", {})
        adopt = "—" if e["competitor"] == "control" else f"{e['adoption']}/{e['n_runs']}"
        print(row([i, e["competitor"], pct(e["cost_reduction_pct"]), adopt,
                   ktok(t.get("input")), ktok(t.get("output")), ktok(t.get("cache"))], W))

    # ---- GSP comparison (Δ vs the same tool without the generous prompt) ----
    if d.get("headline_gsp"):
        print("\n== GENEROUS SYSTEM PROMPT — long sessions, Δ vs base ==")
        print(row(["#", "optimizer", "cost reduction", "Δ vs base", "adoption", "input tok", "output tok", "cache tok"],
                  [3, 24, 16, 12, 12, 12, 12, 12]))
        for i, e in enumerate(d["headline_gsp"], 1):
            t = e.get("tokens", {})
            dl = "—" if e["delta_vs_base_pp"] is None else (f"+{e['delta_vs_base_pp']:.1f}pp" if e["delta_vs_base_pp"] >= 0 else f"{e['delta_vs_base_pp']:.1f}pp")
            print(row([i, e["base"] + "+GSP", pct(e["cost_reduction_pct"]), dl,
                       f"{e['adoption']}/{e['n_runs']}", ktok(t.get("input")), ktok(t.get("output")), ktok(t.get("cache"))],
                      [3, 24, 16, 12, 12, 12, 12, 12]))

    # ---- TOKEN-BAND tables ----
    for b in d["token_bands"]:
        if not b["n_tasks"]:
            continue
        print(f"\n== {b['label']} tokens — {b['n_tasks']} task(s) ==")
        print(row(["#", "optimizer", "cost reduction", "input tok", "output tok", "cache tok"], W[:3] + W[4:]))
        for i, e in enumerate(b["ranking"], 1):
            t = e.get("tokens", {})
            print(row([i, e["competitor"], pct(red_of_ratio(e["aggregate_cost_ratio"])),
                       ktok(t.get("input")), ktok(t.get("output")), ktok(t.get("cache"))], W[:3] + W[4:]))

    # ---- PER-TASK detail (control first, then each tool) ----
    PW = [26, 5, 14, 10, 12, 12, 12]
    order = ["control"] + [e["competitor"] for e in d["headline"] if e["competitor"] != "control"]
    for name in order:
        pt = d["control_per_task"] if name == "control" else d["competitors"].get(name, {}).get("per_task", {})
        print(f"\n== per-task — {name} ==")
        print(row(["task", "runs", "cost reduction", "adoption", "input tok", "output tok", "cache tok"], PW))
        for tk in d["tasks"]:
            p = pt.get(tk)
            if not p:
                continue
            if name == "control":
                cr, adopt = "—", "—"
            else:
                cr = pct(red_of_ratio(p["ratio"]))
                adopt = f"{p['adoption']}/{p['n']}"
            print(row([tk, p["n"], cr, adopt, ktok(p["mean_input_tokens"]),
                       ktok(p["mean_output_tokens"]), ktok(p["mean_cache_tokens"])], PW))


if __name__ == "__main__":
    main()
