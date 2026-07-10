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
#   caveman (npx -y github:JuliusBrussee/caveman#v1.9.0), ponytail (plugin
#   cloned into the sandbox config), claude-context (npx
#   @zilliz/claude-context-mcp@0.1.14, needs OPENAI_API_KEY), claude-mem
#   (npx claude-mem@13.5.4 install), token-optimizer-mcp
#   (npx @ooples/token-optimizer-mcp@5.0.1), claude-token-efficient (CLAUDE.md
#   drop-in @ b32fa8b).
#
# serena is NOT installed: excluded from the board by the COMPETITORS.md
# scope rule (LSP refactoring toolkit, not a token optimizer).
#
# Prerequisites: node>=18 + npm, Rust + cargo, uv, curl. Versions used when
# this board was last run: node v22.21.1, npm 11.6.4.
set -euo pipefail

echo ">> codegraph 0.9.9 (npm)"
npm install -g @colbymchenry/codegraph@0.9.9

echo ">> lean-ctx 3.8.4 (npm prebuilt binary)"
# README also offers install.sh / brew / cargo; we pin the npm binary.
# The full Claude Code integration (`lean-ctx onboard --yes`: hooks, skill,
# CLAUDE.md, permissions) runs per-run inside the sandbox HOME — see
# competitors/lean-ctx/manifest.json setup_commands.
npm install -g lean-ctx-bin@3.8.4

echo ">> rtk v0.42.3 (cargo, from git tag)"
cargo install --git https://github.com/rtk-ai/rtk --tag v0.42.3 rtk

echo ">> squeez 1.22.1 (cargo)"
cargo install squeez@1.22.1

echo ">> graphify 0.8.49 (uv tool, PyPI package 'graphifyy')"
uv tool install graphifyy==0.8.49

echo ">> headroom 0.27.0 (uv tool)"
uv tool install "headroom-ai[all]==0.27.0"

echo ">> code-review-graph 2.3.6 (uv tool)"
uv tool install code-review-graph==2.3.6

echo ">> edgee v0.2.12 (pinned release binary, sha256-verified)"
# README's `curl -fsSL https://edgee.ai/install.sh | bash` installs latest;
# THOL pins the release asset instead so campaigns are reproducible.
EDGEE_URL="https://github.com/edgee-ai/edgee/releases/download/v0.2.12"
EDGEE_TMP="$(mktemp -d)"
curl -fsSL -o "$EDGEE_TMP/edgee" "$EDGEE_URL/edgee.x86_64-unknown-linux-gnu"
curl -fsSL -o "$EDGEE_TMP/edgee.sha256" "$EDGEE_URL/edgee.x86_64-unknown-linux-gnu.sha256"
(cd "$EDGEE_TMP" && sha256sum -c <(awk '{print $1"  edgee"}' edgee.sha256))
install -m755 "$EDGEE_TMP/edgee" "$HOME/.local/bin/edgee"
rm -rf "$EDGEE_TMP"

echo
echo "Installed binaries:"
for b in codegraph lean-ctx rtk squeez graphify headroom code-review-graph edgee; do
  printf '  %-18s ' "$b"; command -v "$b" || echo "(MISSING — check the step above)"
done
echo
echo "Now verify the whole pipeline before a real campaign:"
echo "  python3 runner.py list        # all competitors should appear"
echo "  python3 runner.py selftest    # verifiers must pass on empty workspaces"
echo "  (runner.py run performs a once-per-campaign MCP healthcheck automatically)"
