# Competitor registry

Survey date: **2026-06-10**. Tools that claim to reduce the token
consumption of AI coding agents (Claude Code in particular). A tool enters
the leaderboard when its `competitors/<name>/manifest.json` is marked
`verified: true` — meaning its documented install was reproduced in a
sandboxed config dir and the captured hooks/MCP entries were transcribed
verbatim into the manifest.

## Tier 1 — manifests present in this repo

| name | type | latest version (2026-06-10) | status |
|---|---|---|---|
| control | — (vanilla Claude Code) | — | verified |
| tokenade | MCP + hooks | local install | verified |
| rtk | CLI proxy + hooks | v0.42.3 (60.9k★) | manifest stub |
| codegraph | MCP + index | 0.9.9 (46.6k★) | manifest stub |
| claude-mem | plugin + hooks + MCP | 13.5.4 (81.6k★) | manifest stub |
| serena | MCP (LSP-backed) | git (24.8k★) | manifest stub |
| code-review-graph | MCP + AST graph | pip (18.3k★) | manifest stub |
| claude-context | MCP + embeddings (needs OPENAI_API_KEY) | 0.1.14 (11.8k★) | manifest stub |
| claude-token-efficient | CLAUDE.md drop-in | (5.6k★) | manifest stub |
| lean-ctx | MCP, single binary, ~62 tools | (2.6k★) | manifest stub |
| token-optimizer-mcp | MCP + caching/compression | 5.0.1 npm, repo ahead (405★) | manifest stub |
| squeez | hooks + MCP compressor | (135★, very active) | manifest stub |

## Tier 2 — known, manifest not yet written

token-optimizer (alexgreensh, 1.3k★ external CLI) · cocoindex-code (1.8k★) ·
claude-context-local (231★, stale) · code-context-engine (159★) ·
mcp-memory-keeper (124★) · opencode-codebase-index (107★, OpenCode-first) ·
memory-mcp (97★) · claude-context-optimizer (egorfedorov, 52★, visibility) ·
lazy-mcp (voicetreelab) · lazy-tool (26★) · ecotokens (16★) ·
claude-token-optimizer (nadimtuhin, 464★, prompts+hooks) ·
mcp-gateway (1★) · mcp-context-proxy (0★) · code-index-mcp (trondhindenes, 6★)

## Out of scope

Web scrapers/readers (crawl4ai, firecrawl, trafilatura, defuddle,
readability, jina-reader…), pure usage dashboards (ccusage, claude-usage,
Claude-Code-Usage-Monitor), prompt-compression research libs without a
Claude Code integration (LLMLingua), and anything whose mechanism does not
sit between the agent harness and the model.

## Fairness notes

- Versions are pinned per campaign; re-pinning requires a new campaign, never
  a partial re-run of one tool.
- Memory tools (claude-mem, mcp-memory-keeper, memory-mcp) are designed for
  repeated sessions; THOL runs are single-shot. Their results must carry that
  caveat, and a multi-session task family is the right future fix.
- claude-context's OpenAI embedding spend is external to `total_cost_usd`
  and must be reported separately.
