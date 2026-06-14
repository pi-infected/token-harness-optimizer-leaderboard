# THOL — full results

> Generated snapshot of `python3 leaderboard.py` for the published campaign
> (660+ runs, single Claude Code version). Regenerate with `python3 leaderboard.py`;
> machine-readable form with every raw measurement is in `docs/data/results.json`.

# THOL leaderboard

## Ranking (geometric mean cost ratio vs control, successful runs only — lower is better)

| rank | competitor | agg. cost ratio [95% CI] | vs control | success |
|---|---|---|---|---|
| 1 | tok-mcponly | **1.01** [0.89, 1.11] | ≈ control (n.s.) | 60/60 |
| 2 | tok-hooksonly | **1.02** [0.87, 1.18] | ≈ control (n.s.) | 60/60 |
| 3 | claude-token-efficient | **1.03** [0.95, 1.11] | ≈ control (n.s.) | 60/60 |
| 4 | serena | **1.05** [0.98, 1.14] | ≈ control (n.s.) | 59/60 |
| 5 | lean-ctx | **1.06** [0.98, 1.16] | ≈ control (n.s.) | 59/60 |
| 6 | token-optimizer-mcp | **1.06** [0.99, 1.15] | ≈ control (n.s.) | 60/60 |
| 7 | tokenade | **1.08** [0.93, 1.23] | ≈ control (n.s.) | 60/60 |
| 8 | rtk | **1.08** [0.98, 1.18] | ≈ control (n.s.) | 60/60 |
| 9 | code-review-graph | **1.09** [0.99, 1.22] | ≈ control (n.s.) | 60/60 |
| 10 | squeez | **1.10** [0.93, 1.33] | ≈ control (n.s.) | 60/60 |
| 11 | codegraph | **1.12** [1.04, 1.24] | more expensive (sig.) | 60/60 |

## Control (vanilla Claude Code) noise floor

| task | n | success | mean cost (succ.) | CV |
|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.088 | 2% |
| code-debug-cilog | 3 | 3/3 | $0.077 | 0% |
| code-feature-js | 3 | 3/3 | $0.153 | 21% |
| code-iterate-tests | 3 | 3/3 | $0.116 | 2% |
| code-migration-py | 3 | 3/3 | $0.336 | 61% |
| code-overview-cobra | 3 | 3/3 | $0.264 | 15% |
| code-qa-click | 3 | 3/3 | $0.111 | 38% |
| config-peek | 3 | 3/3 | $0.049 | 0% |
| data-analysis | 3 | 3/3 | $0.065 | 10% |
| data-bigvolume | 3 | 3/3 | $0.060 | 0% |
| doc-digest | 3 | 3/3 | $0.094 | 0% |
| doc-digest-fr | 3 | 3/3 | $0.130 | 0% |
| doc-digest-zh | 3 | 3/3 | $0.130 | 0% |
| html-extract | 3 | 3/3 | $0.072 | 1% |
| log-forensics | 3 | 3/3 | $0.063 | 11% |
| log-needle | 3 | 3/3 | $0.102 | 8% |
| log-needle-zh | 3 | 3/3 | $0.111 | 5% |
| report-pdf | 3 | 3/3 | $0.204 | 12% |
| seo-audit | 3 | 3/3 | $0.260 | 7% |
| writing-brief | 3 | 3/3 | $0.208 | 47% |

## claude-token-efficient (version b32fa8b)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.092 | 1.05 [1.00, 1.12] | 0/3 | 16s |
| code-debug-cilog | 3 | 3/3 | $0.079 | 1.02 [1.01, 1.02] | 0/3 | 9s |
| code-feature-js | 3 | 3/3 | $0.153 | 1.00 [0.80, 1.26] | 0/3 | 45s |
| code-iterate-tests | 3 | 3/3 | $0.123 | 1.06 [1.01, 1.10] | 0/3 | 29s |
| code-migration-py | 3 | 3/3 | $0.247 | 0.73 [0.43, 1.46] | 0/3 | 51s |
| code-overview-cobra | 3 | 3/3 | $0.229 | 0.87 [0.77, 1.02] | 0/3 | 68s |
| code-qa-click | 3 | 3/3 | $0.106 | 0.95 [0.71, 1.58] | 0/3 | 45s |
| config-peek | 3 | 3/3 | $0.050 | 1.03 [1.03, 1.03] | 0/3 | 5s |
| data-analysis | 3 | 3/3 | $0.070 | 1.08 [1.01, 1.21] | 0/3 | 12s |
| data-bigvolume | 3 | 3/3 | $0.060 | 1.00 [0.99, 1.01] | 0/3 | 11s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 9s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.01 [1.01, 1.01] | 0/3 | 13s |
| doc-digest-zh | 3 | 3/3 | $0.133 | 1.02 [1.00, 1.05] | 0/3 | 12s |
| html-extract | 3 | 3/3 | $0.072 | 0.99 [0.98, 1.03] | 0/3 | 11s |
| log-forensics | 3 | 3/3 | $0.070 | 1.10 [0.98, 1.20] | 0/3 | 13s |
| log-needle | 3 | 3/3 | $0.104 | 1.02 [0.97, 1.12] | 0/3 | 21s |
| log-needle-zh | 3 | 3/3 | $0.137 | 1.24 [0.96, 1.60] | 0/3 | 34s |
| report-pdf | 3 | 3/3 | $0.276 | 1.35 [0.92, 2.06] | 0/3 | 97s |
| seo-audit | 3 | 3/3 | $0.254 | 0.98 [0.90, 1.06] | 0/3 | 122s |
| writing-brief | 3 | 3/3 | $0.240 | 1.15 [0.82, 2.33] | 0/3 | 111s |

## code-review-graph (version 2.3.6)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.096 | 1.09 [1.07, 1.12] | 0/3 | 20s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.01, 1.01] | 0/3 | 11s |
| code-feature-js | 3 | 3/3 | $0.150 | 0.98 [0.78, 1.25] | 0/3 | 43s |
| code-iterate-tests | 3 | 3/3 | $0.127 | 1.09 [1.04, 1.13] | 0/3 | 31s |
| code-migration-py | 3 | 3/3 | $0.548 | 1.63 [0.78, 3.70] | 0/3 | 74s |
| code-overview-cobra | 3 | 3/3 | $0.266 | 1.01 [0.84, 1.22] | 0/3 | 78s |
| code-qa-click | 3 | 3/3 | $0.128 | 1.15 [0.88, 1.98] | 0/3 | 51s |
| config-peek | 3 | 3/3 | $0.050 | 1.02 [1.02, 1.02] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.074 | 1.14 [1.07, 1.28] | 0/3 | 15s |
| data-bigvolume | 3 | 3/3 | $0.059 | 1.00 [0.98, 1.01] | 0/3 | 11s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 10s |
| doc-digest-fr | 3 | 3/3 | $0.132 | 1.01 [1.01, 1.02] | 0/3 | 14s |
| doc-digest-zh | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.01] | 0/3 | 13s |
| html-extract | 3 | 3/3 | $0.073 | 1.01 [0.89, 1.08] | 0/3 | 12s |
| log-forensics | 3 | 3/3 | $0.073 | 1.15 [1.03, 1.25] | 0/3 | 18s |
| log-needle | 3 | 3/3 | $0.104 | 1.02 [0.96, 1.11] | 0/3 | 26s |
| log-needle-zh | 3 | 3/3 | $0.164 | 1.48 [0.95, 2.35] | 0/3 | 30s |
| report-pdf | 3 | 3/3 | $0.337 | 1.65 [0.97, 2.20] | 0/3 | 128s |
| seo-audit | 3 | 3/3 | $0.271 | 1.04 [0.97, 1.12] | 0/3 | 127s |
| writing-brief | 3 | 3/3 | $0.148 | 0.71 [0.45, 1.50] | 0/3 | 66s |

## codegraph (version 0.9.9)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.096 | 1.10 [1.08, 1.13] | 0/3 | 25s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.01, 1.01] | 0/3 | 9s |
| code-feature-js | 3 | 3/3 | $0.150 | 0.98 [0.80, 1.23] | 0/3 | 39s |
| code-iterate-tests | 3 | 3/3 | $0.128 | 1.10 [1.05, 1.17] | 0/3 | 33s |
| code-migration-py | 3 | 3/3 | $0.512 | 1.52 [0.93, 3.42] | 0/3 | 66s |
| code-overview-cobra | 3 | 3/3 | $0.273 | 1.04 [0.87, 1.24] | 1/3 | 85s |
| code-qa-click | 3 | 3/3 | $0.168 | 1.52 [1.01, 2.57] | 0/3 | 53s |
| config-peek | 3 | 3/3 | $0.050 | 1.01 [1.01, 1.01] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.072 | 1.11 [0.91, 1.28] | 0/3 | 13s |
| data-bigvolume | 3 | 3/3 | $0.059 | 1.00 [0.99, 1.00] | 0/3 | 16s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.00, 1.01] | 0/3 | 10s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.01] | 0/3 | 12s |
| doc-digest-zh | 3 | 3/3 | $0.132 | 1.01 [1.00, 1.04] | 0/3 | 14s |
| html-extract | 3 | 3/3 | $0.078 | 1.08 [1.08, 1.09] | 0/3 | 13s |
| log-forensics | 3 | 3/3 | $0.077 | 1.22 [1.06, 1.40] | 0/3 | 22s |
| log-needle | 3 | 3/3 | $0.131 | 1.28 [1.13, 1.44] | 0/3 | 30s |
| log-needle-zh | 3 | 3/3 | $0.166 | 1.50 [1.01, 2.35] | 0/3 | 31s |
| report-pdf | 3 | 3/3 | $0.239 | 1.17 [1.00, 1.36] | 0/3 | 104s |
| seo-audit | 3 | 3/3 | $0.261 | 1.00 [0.94, 1.07] | 0/3 | 121s |
| writing-brief | 3 | 3/3 | $0.214 | 1.03 [0.75, 2.23] | 0/3 | 102s |

## lean-ctx (version 3.8.4)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.094 | 1.07 [1.05, 1.10] | 0/3 | 20s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.01, 1.01] | 0/3 | 11s |
| code-feature-js | 3 | 3/3 | $0.154 | 1.01 [0.80, 1.29] | 0/3 | 44s |
| code-iterate-tests | 3 | 3/3 | $0.124 | 1.07 [1.04, 1.10] | 0/3 | 30s |
| code-migration-py | 3 | 3/3 | $0.304 | 0.91 [0.40, 2.06] | 0/3 | 49s |
| code-overview-cobra | 3 | 3/3 | $0.249 | 0.95 [0.72, 1.20] | 1/3 | 126s |
| code-qa-click | 3 | 3/3 | $0.163 | 1.47 [0.99, 2.56] | 0/3 | 63s |
| config-peek | 3 | 3/3 | $0.050 | 1.01 [1.01, 1.01] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.069 | 1.06 [0.89, 1.21] | 0/3 | 12s |
| data-bigvolume | 3 | 3/3 | $0.059 | 0.99 [0.98, 1.01] | 0/3 | 11s |
| doc-digest | 3 | 3/3 | $0.095 | 1.00 [1.00, 1.01] | 0/3 | 12s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.00 [1.00, 1.01] | 0/3 | 14s |
| doc-digest-zh | 3 | 3/3 | $0.132 | 1.01 [1.00, 1.03] | 0/3 | 14s |
| html-extract | 3 | 3/3 | $0.077 | 1.06 [1.04, 1.08] | 0/3 | 14s |
| log-forensics | 3 | 2/3 | $0.073 | 1.16 [1.03, 1.25] | 0/3 | 17s |
| log-needle | 3 | 3/3 | $0.105 | 1.03 [0.94, 1.14] | 0/3 | 24s |
| log-needle-zh | 3 | 3/3 | $0.170 | 1.53 [0.93, 2.38] | 0/3 | 34s |
| report-pdf | 3 | 3/3 | $0.201 | 0.98 [0.86, 1.12] | 0/3 | 88s |
| seo-audit | 3 | 3/3 | $0.263 | 1.01 [0.94, 1.09] | 0/3 | 124s |
| writing-brief | 3 | 3/3 | $0.214 | 1.03 [0.74, 2.23] | 0/3 | 100s |

## rtk (version v0.42.3)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.091 | 1.04 [1.02, 1.07] | 0/3 | 17s |
| code-debug-cilog | 3 | 3/3 | $0.080 | 1.04 [1.03, 1.04] | 0/3 | 10s |
| code-feature-js | 3 | 3/3 | $0.164 | 1.07 [0.79, 1.42] | 0/3 | 49s |
| code-iterate-tests | 3 | 3/3 | $0.128 | 1.11 [1.03, 1.21] | 0/3 | 30s |
| code-migration-py | 3 | 3/3 | $0.315 | 0.94 [0.33, 2.37] | 0/3 | 53s |
| code-overview-cobra | 3 | 3/3 | $0.190 | 0.72 [0.48, 0.98] | 0/3 | 90s |
| code-qa-click | 3 | 3/3 | $0.155 | 1.39 [0.94, 2.38] | 0/3 | 68s |
| config-peek | 3 | 3/3 | $0.051 | 1.05 [1.05, 1.05] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.072 | 1.11 [1.04, 1.24] | 0/3 | 12s |
| data-bigvolume | 3 | 3/3 | $0.068 | 1.14 [1.01, 1.38] | 0/3 | 13s |
| doc-digest | 3 | 3/3 | $0.097 | 1.03 [1.02, 1.03] | 0/3 | 10s |
| doc-digest-fr | 3 | 3/3 | $0.134 | 1.03 [1.02, 1.06] | 0/3 | 12s |
| doc-digest-zh | 3 | 3/3 | $0.136 | 1.04 [1.02, 1.05] | 0/3 | 14s |
| html-extract | 3 | 3/3 | $0.075 | 1.04 [1.03, 1.05] | 0/3 | 11s |
| log-forensics | 3 | 3/3 | $0.072 | 1.14 [1.00, 1.30] | 0/3 | 15s |
| log-needle | 3 | 3/3 | $0.126 | 1.23 [1.06, 1.41] | 0/3 | 31s |
| log-needle-zh | 3 | 3/3 | $0.121 | 1.09 [1.03, 1.16] | 0/3 | 27s |
| report-pdf | 3 | 3/3 | $0.252 | 1.23 [1.07, 1.42] | 0/3 | 108s |
| seo-audit | 3 | 3/3 | $0.286 | 1.10 [0.92, 1.36] | 0/3 | 133s |
| writing-brief | 3 | 3/3 | $0.270 | 1.30 [1.00, 2.79] | 0/3 | 120s |

## serena (version v1.5.3)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.092 | 1.05 [1.04, 1.08] | 0/3 | 17s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.00, 1.02] | 0/3 | 10s |
| code-feature-js | 3 | 3/3 | $0.144 | 0.94 [0.70, 1.26] | 0/3 | 43s |
| code-iterate-tests | 3 | 3/3 | $0.120 | 1.03 [1.02, 1.05] | 0/3 | 29s |
| code-migration-py | 3 | 3/3 | $0.459 | 1.37 [0.83, 3.08] | 0/3 | 73s |
| code-overview-cobra | 3 | 3/3 | $0.224 | 0.85 [0.74, 1.01] | 0/3 | 101s |
| code-qa-click | 3 | 3/3 | $0.146 | 1.32 [0.77, 2.29] | 0/3 | 58s |
| config-peek | 3 | 3/3 | $0.049 | 1.01 [1.01, 1.01] | 0/3 | 5s |
| data-analysis | 3 | 3/3 | $0.060 | 0.93 [0.87, 1.04] | 0/3 | 11s |
| data-bigvolume | 3 | 3/3 | $0.060 | 1.01 [0.99, 1.04] | 0/3 | 12s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 11s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.00 [1.00, 1.01] | 0/3 | 12s |
| doc-digest-zh | 3 | 3/3 | $0.133 | 1.02 [1.00, 1.04] | 0/3 | 15s |
| html-extract | 3 | 3/3 | $0.074 | 1.02 [1.00, 1.06] | 0/3 | 13s |
| log-forensics | 3 | 2/3 | $0.071 | 1.12 [1.00, 1.21] | 0/3 | 17s |
| log-needle | 3 | 3/3 | $0.109 | 1.07 [0.92, 1.27] | 0/3 | 25s |
| log-needle-zh | 3 | 3/3 | $0.119 | 1.07 [1.02, 1.12] | 0/3 | 34s |
| report-pdf | 3 | 3/3 | $0.238 | 1.16 [0.92, 1.42] | 0/3 | 105s |
| seo-audit | 3 | 3/3 | $0.258 | 1.00 [0.92, 1.08] | 0/3 | 121s |
| writing-brief | 3 | 3/3 | $0.218 | 1.05 [0.68, 2.21] | 0/3 | 106s |

## squeez (version 1.22.1)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.116 | 1.32 [1.26, 1.38] | 0/3 | 28s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.01, 1.02] | 0/3 | 9s |
| code-feature-js | 3 | 3/3 | $0.193 | 1.26 [0.84, 1.83] | 0/3 | 63s |
| code-iterate-tests | 3 | 3/3 | $0.142 | 1.22 [1.16, 1.27] | 0/3 | 34s |
| code-migration-py | 3 | 3/3 | $0.131 | 0.39 [0.24, 0.87] | 0/3 | 34s |
| code-overview-cobra | 3 | 3/3 | $0.235 | 0.89 [0.72, 1.10] | 0/3 | 114s |
| code-qa-click | 3 | 3/3 | $0.112 | 1.01 [0.73, 1.71] | 0/3 | 54s |
| config-peek | 3 | 3/3 | $0.051 | 1.03 [1.03, 1.03] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.068 | 1.05 [0.99, 1.18] | 0/3 | 14s |
| data-bigvolume | 3 | 3/3 | $0.059 | 0.99 [0.99, 0.99] | 0/3 | 13s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.00, 1.01] | 0/3 | 10s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.01] | 0/3 | 14s |
| doc-digest-zh | 3 | 3/3 | $0.134 | 1.03 [1.00, 1.04] | 0/3 | 15s |
| html-extract | 3 | 3/3 | $0.069 | 0.95 [0.89, 0.98] | 0/3 | 11s |
| log-forensics | 3 | 3/3 | $0.068 | 1.07 [0.96, 1.16] | 0/3 | 17s |
| log-needle | 3 | 3/3 | $0.159 | 1.56 [1.05, 2.41] | 0/3 | 26s |
| log-needle-zh | 3 | 3/3 | $0.436 | 3.94 [3.53, 4.49] | 0/3 | 52s |
| report-pdf | 3 | 3/3 | $0.249 | 1.22 [1.02, 1.45] | 0/3 | 105s |
| seo-audit | 3 | 3/3 | $0.344 | 1.32 [1.16, 1.50] | 0/3 | 165s |
| writing-brief | 3 | 3/3 | $0.185 | 0.89 [0.43, 1.88] | 0/3 | 85s |

## tok-hooksonly (version 0.5.1)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.088 | 1.00 [0.98, 1.03] | 0/3 | 19s |
| code-debug-cilog | 3 | 3/3 | $0.071 | 0.92 [0.91, 0.94] | 0/3 | 11s |
| code-feature-js | 3 | 3/3 | $0.108 | 0.71 [0.57, 0.89] | 0/3 | 26s |
| code-iterate-tests | 3 | 3/3 | $0.129 | 1.11 [1.00, 1.30] | 0/3 | 64s |
| code-migration-py | 3 | 3/3 | $0.127 | 0.38 [0.23, 0.86] | 0/3 | 31s |
| code-overview-cobra | 3 | 3/3 | $0.218 | 0.83 [0.64, 1.06] | 0/3 | 81s |
| code-qa-click | 3 | 3/3 | $0.134 | 1.20 [0.88, 1.99] | 0/3 | 64s |
| config-peek | 3 | 3/3 | $0.049 | 1.00 [1.00, 1.00] | 0/3 | 6s |
| data-analysis | 3 | 3/3 | $0.062 | 0.96 [0.86, 1.08] | 0/3 | 12s |
| data-bigvolume | 3 | 3/3 | $0.059 | 1.00 [0.99, 1.00] | 0/3 | 12s |
| doc-digest | 3 | 3/3 | $0.095 | 1.00 [1.00, 1.00] | 0/3 | 11s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.02] | 0/3 | 13s |
| doc-digest-zh | 3 | 3/3 | $0.132 | 1.01 [0.99, 1.03] | 0/3 | 13s |
| html-extract | 3 | 3/3 | $0.072 | 1.00 [0.97, 1.01] | 0/3 | 12s |
| log-forensics | 3 | 3/3 | $0.064 | 1.01 [0.89, 1.12] | 0/3 | 13s |
| log-needle | 3 | 3/3 | $0.183 | 1.80 [0.91, 3.45] | 0/3 | 33s |
| log-needle-zh | 3 | 3/3 | $0.210 | 1.90 [1.09, 3.39] | 0/3 | 36s |
| report-pdf | 3 | 3/3 | $0.298 | 1.46 [1.28, 1.64] | 0/3 | 129s |
| seo-audit | 3 | 3/3 | $0.307 | 1.18 [1.10, 1.27] | 0/3 | 133s |
| writing-brief | 3 | 3/3 | $0.203 | 0.97 [0.59, 2.07] | 0/3 | 95s |

## tok-mcponly (version 0.5.1)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.096 | 1.09 [1.07, 1.12] | 0/3 | 20s |
| code-debug-cilog | 3 | 3/3 | $0.079 | 1.02 [1.01, 1.02] | 0/3 | 12s |
| code-feature-js | 3 | 3/3 | $0.164 | 1.07 [0.73, 1.54] | 0/3 | 49s |
| code-iterate-tests | 3 | 3/3 | $0.129 | 1.11 [1.07, 1.15] | 0/3 | 29s |
| code-migration-py | 3 | 3/3 | $0.134 | 0.40 [0.25, 0.90] | 3/3 | 34s |
| code-overview-cobra | 3 | 3/3 | $0.268 | 1.02 [0.79, 1.29] | 0/3 | 108s |
| code-qa-click | 3 | 3/3 | $0.144 | 1.30 [0.87, 2.26] | 0/3 | 55s |
| config-peek | 3 | 3/3 | $0.050 | 1.02 [1.02, 1.02] | 0/3 | 5s |
| data-analysis | 3 | 3/3 | $0.071 | 1.10 [0.92, 1.26] | 0/3 | 16s |
| data-bigvolume | 3 | 3/3 | $0.060 | 1.01 [1.01, 1.02] | 0/3 | 12s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 10s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.01] | 0/3 | 13s |
| doc-digest-zh | 3 | 3/3 | $0.131 | 1.01 [1.00, 1.01] | 0/3 | 12s |
| html-extract | 3 | 3/3 | $0.081 | 1.12 [1.08, 1.14] | 0/3 | 12s |
| log-forensics | 3 | 3/3 | $0.075 | 1.19 [1.05, 1.34] | 0/3 | 17s |
| log-needle | 3 | 3/3 | $0.119 | 1.16 [0.90, 1.51] | 0/3 | 32s |
| log-needle-zh | 3 | 3/3 | $0.117 | 1.06 [0.97, 1.15] | 0/3 | 33s |
| report-pdf | 3 | 3/3 | $0.217 | 1.06 [0.94, 1.17] | 0/3 | 92s |
| seo-audit | 3 | 3/3 | $0.278 | 1.07 [0.99, 1.16] | 0/3 | 138s |
| writing-brief | 3 | 3/3 | $0.174 | 0.83 [0.47, 1.81] | 0/3 | 78s |

## token-optimizer-mcp (version 5.0.1)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.096 | 1.09 [1.07, 1.12] | 0/3 | 21s |
| code-debug-cilog | 3 | 3/3 | $0.078 | 1.01 [1.01, 1.01] | 0/3 | 10s |
| code-feature-js | 3 | 3/3 | $0.145 | 0.95 [0.72, 1.27] | 0/3 | 41s |
| code-iterate-tests | 3 | 3/3 | $0.129 | 1.11 [1.07, 1.15] | 0/3 | 29s |
| code-migration-py | 3 | 3/3 | $0.363 | 1.08 [0.48, 2.42] | 0/3 | 54s |
| code-overview-cobra | 3 | 3/3 | $0.216 | 0.82 [0.68, 0.98] | 0/3 | 80s |
| code-qa-click | 3 | 3/3 | $0.131 | 1.18 [0.80, 1.98] | 0/3 | 51s |
| config-peek | 3 | 3/3 | $0.050 | 1.02 [1.02, 1.02] | 0/3 | 5s |
| data-analysis | 3 | 3/3 | $0.065 | 1.00 [0.87, 1.16] | 0/3 | 12s |
| data-bigvolume | 3 | 3/3 | $0.069 | 1.16 [0.98, 1.24] | 0/3 | 14s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 12s |
| doc-digest-fr | 3 | 3/3 | $0.131 | 1.00 [1.00, 1.01] | 0/3 | 13s |
| doc-digest-zh | 3 | 3/3 | $0.134 | 1.03 [1.00, 1.05] | 0/3 | 16s |
| html-extract | 3 | 3/3 | $0.080 | 1.10 [1.09, 1.11] | 0/3 | 13s |
| log-forensics | 3 | 3/3 | $0.077 | 1.22 [1.07, 1.39] | 0/3 | 21s |
| log-needle | 3 | 3/3 | $0.107 | 1.05 [0.95, 1.16] | 0/3 | 27s |
| log-needle-zh | 3 | 3/3 | $0.122 | 1.10 [0.97, 1.22] | 0/3 | 32s |
| report-pdf | 3 | 3/3 | $0.238 | 1.17 [0.99, 1.37] | 0/3 | 100s |
| seo-audit | 3 | 3/3 | $0.255 | 0.98 [0.90, 1.07] | 0/3 | 122s |
| writing-brief | 3 | 3/3 | $0.261 | 1.25 [0.70, 2.62] | 0/3 | 117s |

## tokenade (version 0.5.6)

| task | n | success | mean cost (succ.) | cost ratio vs control [95% CI] | adoption | mean wall |
|---|---|---|---|---|---|---|
| code-bugfix-py | 3 | 3/3 | $0.095 | 1.08 [1.06, 1.11] | 0/3 | 20s |
| code-debug-cilog | 3 | 3/3 | $0.073 | 0.95 [0.94, 0.95] | 0/3 | 14s |
| code-feature-js | 3 | 3/3 | $0.201 | 1.31 [1.05, 1.66] | 0/3 | 64s |
| code-iterate-tests | 3 | 3/3 | $0.136 | 1.17 [1.06, 1.24] | 0/3 | 37s |
| code-migration-py | 3 | 3/3 | $0.125 | 0.37 [0.22, 0.84] | 3/3 | 33s |
| code-overview-cobra | 3 | 3/3 | $0.283 | 1.07 [0.85, 1.34] | 1/3 | 102s |
| code-qa-click | 3 | 3/3 | $0.134 | 1.20 [0.92, 2.06] | 0/3 | 58s |
| config-peek | 3 | 3/3 | $0.050 | 1.01 [1.01, 1.01] | 0/3 | 8s |
| data-analysis | 3 | 3/3 | $0.061 | 0.94 [0.86, 1.06] | 0/3 | 11s |
| data-bigvolume | 3 | 3/3 | $0.066 | 1.10 [1.01, 1.26] | 0/3 | 14s |
| doc-digest | 3 | 3/3 | $0.095 | 1.01 [1.01, 1.01] | 0/3 | 11s |
| doc-digest-fr | 3 | 3/3 | $0.138 | 1.06 [1.00, 1.17] | 0/3 | 12s |
| doc-digest-zh | 3 | 3/3 | $0.134 | 1.03 [1.00, 1.05] | 0/3 | 17s |
| html-extract | 3 | 3/3 | $0.075 | 1.04 [1.03, 1.04] | 0/3 | 11s |
| log-forensics | 3 | 3/3 | $0.073 | 1.15 [1.03, 1.25] | 0/3 | 16s |
| log-needle | 3 | 3/3 | $0.110 | 1.08 [1.03, 1.19] | 0/3 | 28s |
| log-needle-zh | 3 | 3/3 | $0.219 | 1.98 [1.17, 3.46] | 0/3 | 43s |
| report-pdf | 3 | 3/3 | $0.303 | 1.48 [0.95, 2.30] | 0/3 | 122s |
| seo-audit | 3 | 3/3 | $0.297 | 1.14 [1.00, 1.33] | 0/3 | 115s |
| writing-brief | 3 | 3/3 | $0.248 | 1.19 [0.80, 2.52] | 0/3 | 119s |
