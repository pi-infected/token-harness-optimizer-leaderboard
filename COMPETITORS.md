# Competitor registry

Survey date: **2026-06-10** (edgee added 2026-07-10). Tools that claim to
reduce the token consumption of AI coding agents (Claude Code in particular).

## Inclusion rule (scope, 2026-07)

A tool qualifies for the board when its **primary, documented mechanism is
reducing the token cost of coding-agent sessions**: output/context
compression or compaction, context budgeting or indexing sold on cheaper
retrieval, output shaping, or proxy-side request compression. A tool whose
primary function is something else (a code-navigation/refactoring toolkit, a
memory system, a general agent framework) is **out of scope even if it
claims token savings as a side benefit** — benchmarking it here would grade
it on a race it isn't running.

Two judgement calls under this rule, recorded openly:

- **serena** (oraios) — excluded 2026-07. LSP-backed symbol-level
  retrieval/editing toolkit; token efficiency is a claimed side benefit of
  its retrieval style, not the product's function. Its 2.1.183 campaign rows
  stay in the published DB, flagged `excluded_arms` in results.json.
- **codegraph / code-review-graph / graphify** — kept. Their READMEs pitch
  cheaper context retrieval (token cost) as the primary value proposition,
  not general code intelligence.

A tool enters the leaderboard when its `competitors/<name>/manifest.json`
is marked `verified: true` — meaning its documented install was reproduced
in a sandboxed config dir and the captured hooks/MCP entries were
transcribed verbatim into the manifest (or the install was validated by a
full campaign: every run's setup completed rc=0). Arms run with
`--allow-unverified` are never published.

## Tier 1 — manifests present in this repo

| name | type | latest version (survey) | status |
|---|---|---|---|
| control | — (vanilla Claude Code) | — | verified |
| tokenade | hooks + CLI | local install | verified |
| edgee | proxy gateway (ANTHROPIC_BASE_URL) | v0.2.12 (111★) | verified 2026-07-10 |
| rtk | CLI proxy + hooks | v0.42.3 (60.9k★) | verified |
| codegraph | MCP + index | 0.9.9 (46.6k★) | verified |
| claude-mem | plugin + hooks + MCP | 13.5.4 (81.6k★) | manifest stub |
| code-review-graph | MCP + AST graph | 2.3.6 (18.3k★) | verified |
| claude-context | MCP + embeddings (needs OPENAI_API_KEY) | 0.1.14 (11.8k★) | manifest stub |
| claude-token-efficient | CLAUDE.md drop-in | (5.6k★) | verified |
| lean-ctx | hooks + MCP, single binary | 3.8.4 (2.6k★) | verified — manifest fixed 2026-07-09 (full `onboard` install); 2.1.183 arm excluded pending re-run |
| graphify | CLI + skill | 0.8.49 | verified (campaign-validated) |
| caveman | skill + SessionStart hook | v1.9.0 | verified (campaign-validated) |
| ponytail | plugin + lifecycle hooks | main | verified (campaign-validated) |
| headroom | proxy (wrap) | 0.27.0 | verified (campaign-validated) |
| token-optimizer-mcp | MCP + caching/compression | 5.0.1 npm (405★) | manifest stub |
| squeez | hooks + MCP compressor | 1.22.1 (135★) | verified |

## Tier 2 — known, manifest not yet written

token-optimizer (alexgreensh, 1.3k★ external CLI) · cocoindex-code (1.8k★) ·
claude-context-local (231★, stale) · code-context-engine (159★) ·
mcp-memory-keeper (124★) · opencode-codebase-index (107★, OpenCode-first) ·
memory-mcp (97★) · claude-context-optimizer (egorfedorov, 52★, visibility) ·
lazy-mcp (voicetreelab) · lazy-tool (26★) · ecotokens (16★) ·
claude-token-optimizer (nadimtuhin, 464★, prompts+hooks) ·
mcp-gateway (1★) · mcp-context-proxy (0★) · code-index-mcp (trondhindenes, 6★)

## Out of scope

serena (see inclusion rule above) · web scrapers/readers (crawl4ai,
firecrawl, trafilatura, defuddle, readability, jina-reader…) · pure usage
dashboards (ccusage, claude-usage, Claude-Code-Usage-Monitor) ·
prompt-compression research libs without a Claude Code integration
(LLMLingua) · anything whose mechanism does not sit between the agent
harness and the model.

## Fairness notes

- Versions are pinned per campaign; re-pinning requires a new campaign, never
  a partial re-run of one tool.
- Before any campaign, every declared MCP server passes a once-per-campaign
  stdio healthcheck (`runner.py` does this automatically, in a throwaway
  sandbox, without spawning a Claude session) — a broken server can never
  masquerade as "the agent ignored the tool".
- Memory tools (claude-mem, mcp-memory-keeper, memory-mcp) are designed for
  repeated sessions; THOL runs are single-shot. Their results must carry that
  caveat, and a multi-session task family is the right future fix.
- claude-context's OpenAI embedding spend is external to `total_cost_usd`
  and must be reported separately.
- edgee's official `edgee launch claude` flow requires an Edgee cloud
  account; THOL runs its auth-free `edgee local-gateway` (same compression
  pipeline) — a documented deviation in its manifest.
