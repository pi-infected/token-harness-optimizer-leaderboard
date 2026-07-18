#!/usr/bin/env bash
# Bench remaining tools ONE AT A TIME (each fully finishes before the next starts)
# to avoid concurrent-session /login prompts. Resume-safe per competitor.
cd /home/infected/.cursor-tutor/projects/token-harness-optimizer-leaderboard
export DISABLE_AUTOUPDATER=1
# The campaign of record. The runner aborts if the harness on PATH is not this
# version, so a pruned or repointed .claude-pin never measures under another.
export THOL_CAMPAIGN=2.1.206
# Strip the tokenade shim from the runner's OWN PATH: its `git` wrapper can
# point at a stale temp binary from a parallel tokenade session and exit 127,
# crashing the runner's workspace-prep git checkout (build_env already strips
# it for the sandboxed runs, but not for the runner process itself).
export PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '/.tokenade/' | paste -sd:)"
TOOLS="rtk codegraph code-review-graph claude-token-efficient lean-ctx graphify caveman ponytail headroom squeez"
# web-research-oss-inventory timeout_s was raised 1800 -> 2400: headroom drives
# ~2.5x web calls there (110 WebSearch + 31 WebFetch) and its proxy latency put
# wall at ~1850s, riding the old 1800s cap. 2400s lets it complete (real work
# finished ~1853s). Other tools finish in 558-1300s, unaffected.
for t in $TOOLS; do
  echo "=================== $(date '+%F %T') START $t ==================="
  python3 runner.py run --competitors "$t" --reps 10 --max-consecutive-errors 5
  rc=$?
  echo "=================== $(date '+%F %T') END $t (rc=$rc) ==================="
  # rc!=0 => garde a coupé (quota/auth). On stoppe la chaîne pour ne pas
  # enchaîner des échecs; relance manuelle après reset.
  if [ $rc -ne 0 ]; then echo "!! chaîne stoppée sur $t (rc=$rc) — relancer après reset quota"; exit $rc; fi
done
echo "=================== $(date '+%F %T') TOUS LES OUTILS FINIS ==================="
