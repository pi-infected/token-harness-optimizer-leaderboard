Build the most COMPLETE inventory you can of open-source projects for **reducing /
optimizing LLM token usage**, and output it as JSON.

You are given NO URLs. Use your web tools (WebSearch + WebFetch) NOW, in this session,
to find projects. Cover every sub-area you can, e.g.: prompt compression / context
distillation, retrieval / RAG context compression, KV-cache compression, long-context
memory, token-efficient developer tooling (CLI proxies, agent-harness output compactors,
repo-to-prompt packers, MCP result folders), tokenizers / token counting, semantic /
prompt caching.

CRITICAL RULES — read carefully, you are scored on the final answer of THIS session:
- Work SYNCHRONOUSLY, right now, in this conversation. Do the searching and fetching
  yourself, turn by turn, until you have gathered as many real projects as you can.
- Do NOT defer the work. Do NOT say "I'll run this in the background", "this is running
  as a workflow", or "I'll notify you when it completes". There is NO background process
  and no later turn — if you promise to answer later, you score ZERO.
- Keep issuing WebSearch/WebFetch calls to widen coverage (awesome-lists, GitHub topic
  pages, papers-with-code, package registries are high-yield), then STOP and answer.
- Your FINAL message MUST contain the complete inventory as a single fenced ```json code
  block: a JSON array where each element is
  {"name": "...", "url": "https://github.com/owner/repo", "description": "..."}.
  Include the GitHub URL (owner/repo) for every project — that is exactly what is checked.
  More real projects with correct GitHub URLs = higher score.

Begin searching now, and end this session with the ```json inventory.
