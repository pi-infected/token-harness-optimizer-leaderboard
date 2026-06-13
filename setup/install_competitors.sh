#!/usr/bin/env bash
# THOL — install the host-level binaries that competitors with a `requires`
# entry expect on $PATH. The runner checks `requires` BEFORE running a
# competitor's per-run setup_commands, so these binaries must exist globally
# (exactly like a real user who followed each tool's README would have them).
#
# Every command below is transcribed verbatim from the matching
# competitors/<name>/manifest.json `install_doc` (the upstream README step),
# with the pinned version. Idempotent: re-running is safe.
#
# Tools NOT listed here need no global binary — the runner launches them via
# npx / their MCP entry / a dropped-in file, fully inside the per-run sandbox:
#   claude-context (npx @zilliz/claude-context-mcp@0.1.14, needs OPENAI_API_KEY),
#   claude-mem (npx claude-mem@13.5.4 install), token-optimizer-mcp
#   (npx @ooples/token-optimizer-mcp@5.0.1), claude-token-efficient (CLAUDE.md
#   drop-in @ b32fa8b), code-review-graph (pip, CLI self-registers MCP).
#
# Prerequisites: node>=18 + npm, Rust + cargo, uv. Versions used when this
# board was last run: node v22.21.1, npm 11.6.4.
set -euo pipefail

echo ">> codegraph 0.9.9 (npm)"
npm install -g @colbymchenry/codegraph@0.9.9

echo ">> lean-ctx 3.8.4 (npm prebuilt binary)"
# README also offers install.sh / brew / cargo; we pin the npm binary.
# Do NOT run `lean-ctx onboard`: it rewrites your shell rc with a hook.
npm install -g lean-ctx-bin@3.8.4

echo ">> rtk v0.42.3 (cargo, from git tag)"
cargo install --git https://github.com/rtk-ai/rtk --tag v0.42.3 rtk

echo ">> squeez 1.22.1 (cargo)"
cargo install squeez@1.22.1

echo ">> serena v1.5.3 (uv tool, from git)"
uv tool install --from git+https://github.com/oraios/serena@v1.5.3 serena

echo
echo "Installed binaries:"
for b in codegraph lean-ctx rtk squeez serena; do
  printf '  %-10s ' "$b"; command -v "$b" || echo "(MISSING — check the step above)"
done
echo
echo "Now verify the whole pipeline before a real campaign:"
echo "  python3 runner.py list        # all competitors should appear"
echo "  python3 runner.py selftest    # verifiers must pass on empty workspaces"
