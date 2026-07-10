import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import answer, emit

# Hidden ground-truth key (verify.py is never in the agent's workspace).
# Recall = (# reference projects the agent's inventory recovers) / (total).
# A project counts as FOUND if the answer text contains a DISTINCTIVE term for it:
# its github slug "owner/repo", its repo name, its url, its full name, or a
# distinctive alias. Short/generic terms (len<7, no '-'/'/') are ignored to avoid
# false positives from ordinary English words (e.g. "quest", "h2o", "compact").
GROUND = [
    {"name":"LLMLingua","slug":"microsoft/llmlingua","aliases":["llmlingua","longllmlingua","llmlingua-2","llmlingua2"]},
    {"name":"AutoCompressors","slug":"princeton-nlp/autocompressors","aliases":["autocompressors","auto-compressors"]},
    {"name":"In-context Autoencoder","slug":"getao/icae","aliases":["in-context autoencoder"]},
    {"name":"Gisting","slug":"jayelm/gisting","aliases":["gisting","gist tokens"]},
    {"name":"xRAG","slug":"hannibal046/xrag","aliases":["xrag"]},
    {"name":"Selective Context","slug":"liyucheng09/selective_context","aliases":["selective_context","selective-context","selective context"]},
    {"name":"PCToolkit","slug":"3dagentworld/toolkit-for-prompt-compression","aliases":["pctoolkit","toolkit-for-prompt-compression"]},
    {"name":"500xCompressor","slug":"zongqianli/500xcompressor","aliases":["500xcompressor"]},
    {"name":"CompAct","slug":"dmis-lab/compact","aliases":[]},
    {"name":"Prompt-Compression-Survey","slug":"zongqianli/prompt-compression-survey","aliases":["prompt-compression-survey"]},
    {"name":"RECOMP","slug":"carriex/recomp","aliases":["recomp"]},
    {"name":"LLoCO","slug":"jeffreysijuntan/lloco","aliases":["lloco"]},
    {"name":"FlexRAG","slug":"wcyno23/flexrag","aliases":["flexrag"]},
    {"name":"CEPE","slug":"princeton-nlp/cepe","aliases":[]},
    {"name":"H2O Heavy-Hitter Oracle","slug":"fminference/h2o","aliases":["heavy-hitter-oracle","heavy hitter oracle"]},
    {"name":"KVQuant","slug":"squeezeailab/kvquant","aliases":["kvquant","kv-quant"]},
    {"name":"KIVI","slug":"jy-yuan/kivi","aliases":[]},
    {"name":"StreamingLLM","slug":"mit-han-lab/streaming-llm","aliases":["streaming-llm","streamingllm","streaming_llm"]},
    {"name":"SnapKV","slug":"fasterdecoding/snapkv","aliases":["snapkv","snap-kv"]},
    {"name":"PyramidKV","slug":"zefan-cai/kvcache-factory","aliases":["pyramidkv","pyramid-kv","kvcache-factory"]},
    {"name":"MInference","slug":"microsoft/minference","aliases":["minference"]},
    {"name":"Quest","slug":"mit-han-lab/quest","aliases":[]},
    {"name":"LMCache","slug":"lmcache/lmcache","aliases":["lmcache","lm-cache"]},
    {"name":"InfLLM","slug":"thunlp/infllm","aliases":["infllm","inf-llm"]},
    {"name":"Activation Beacon","slug":"flagopen/flagembedding","aliases":["activation-beacon","activation beacon","flagembedding"]},
    {"name":"Letta MemGPT","slug":"letta-ai/letta","aliases":["memgpt","cpacker/memgpt","letta-ai"]},
    {"name":"tiktoken","slug":"openai/tiktoken","aliases":[]},
    {"name":"HuggingFace Tokenizers","slug":"huggingface/tokenizers","aliases":["hf-tokenizers","huggingface tokenizers"]},
    {"name":"TokenCost","slug":"agentops-ai/tokencost","aliases":["tokencost"]},
    {"name":"GPT-3-Encoder","slug":"latitudegames/gpt-3-encoder","aliases":["gpt-3-encoder","gpt3-encoder"]},
    {"name":"js-tiktoken","slug":"dqbd/tiktoken","aliases":["js-tiktoken","dqbd/tiktoken"]},
    {"name":"tiktoken-go","slug":"pkoukk/tiktoken-go","aliases":["tiktoken-go"]},
    {"name":"SentencePiece","slug":"google/sentencepiece","aliases":["sentencepiece"]},
    {"name":"llama-tokenizer-js","slug":"belladoreai/llama-tokenizer-js","aliases":["llama-tokenizer-js","llama-tokenizer"]},
    {"name":"ttok","slug":"simonw/ttok","aliases":["simonw/ttok"]},
    {"name":"GPTCache","slug":"zilliztech/gptcache","aliases":["gptcache"]},
    {"name":"LiteLLM","slug":"berriai/litellm","aliases":["litellm"]},
    {"name":"RouteLLM","slug":"lm-sys/routellm","aliases":["routellm"]},
    {"name":"vCache","slug":"vcache-project/vcache","aliases":["vcache-project"]},
    {"name":"ModelCache","slug":"codefuse-ai/modelcache","aliases":["modelcache"]},
    {"name":"RTK Rust Token Killer","slug":"rtk-ai/rtk","aliases":["rust token killer","rtk-ai"]},
    {"name":"snip","slug":"edouard-claude/snip","aliases":["edouard-claude/snip"]},
    {"name":"clauditor","slug":"iyadhkhalfallah/clauditor","aliases":["clauditor"]},
    {"name":"GrapeRoot","slug":"kunal12203/codex-cli-compact","aliases":["graperoot","graperoot.dev","codex-cli-compact"]},
    {"name":"LeanCTX","slug":"yvgude/lean-ctx","aliases":["lean-ctx","leanctx"]},
    {"name":"context-mode","slug":"mksglu/context-mode","aliases":["context-mode"]},
    {"name":"token-optimizer","slug":"alexgreensh/token-optimizer","aliases":["alexgreensh/token-optimizer"]},
    {"name":"token-optimizer-mcp","slug":"ooples/token-optimizer-mcp","aliases":["token-optimizer-mcp"]},
    {"name":"token-reducer","slug":"madhan230205/token-reducer","aliases":["madhan230205/token-reducer","token-reducer"]},
    {"name":"Repomix","slug":"yamadashy/repomix","aliases":["repomix"]},
    {"name":"code2prompt","slug":"mufeedvh/code2prompt","aliases":["code2prompt"]},
    {"name":"files-to-prompt","slug":"simonw/files-to-prompt","aliases":["files-to-prompt"]},
    {"name":"ai-digest","slug":"khromov/ai-digest","aliases":["khromov/ai-digest"]},
    {"name":"Gitingest","slug":"coderamp-labs/gitingest","aliases":["gitingest","cyclotruc/gitingest"]},
    {"name":"Serena","slug":"oraios/serena","aliases":["oraios/serena"]},
    {"name":"Context7","slug":"upstash/context7","aliases":["context7"]},
    {"name":"ctx-wire","slug":"","aliases":["ctx-wire","ctxwire","ctx-wire.dev"]},
]

STOP = {"compact", "context", "quest", "beacon", "gist", "letta", "serena"}


def terms_for(p):
    ts = set()
    if p["slug"]:
        ts.add(p["slug"])
        ts.add(p["slug"].split("/")[-1])
    ts.add(p["name"])
    ts.update(p["aliases"])
    out = set()
    for t in ts:
        t = t.lower().strip()
        if not t:
            continue
        # keep only distinctive terms: contain '/' or '-' or are long enough
        if ("/" in t) or ("-" in t) or (len(t) >= 7):
            if t not in STOP:
                out.add(t)
    return out


a = answer().lower()
found, missed = [], []
for p in GROUND:
    if any(t in a for t in terms_for(p)):
        found.append(p["name"])
    else:
        missed.append(p["name"])

# how many total projects the agent listed (rough: count github.com/owner/repo refs)
listed = len(set(re.findall(r"github\.com/[\w.-]+/[\w.-]+", a)))

recall = len(found) / len(GROUND)
emit(recall, f"recall={recall:.3f} found={len(found)}/{len(GROUND)} listed_urls={listed} | "
             f"FOUND={sorted(found)} | MISSED={sorted(missed)}")
