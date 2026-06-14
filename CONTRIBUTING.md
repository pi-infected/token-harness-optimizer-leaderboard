# Contributing to THOL

THOL ranks token-optimizer tools for coding agents. Because the benchmark is
maintained by the author of one of the measured tools (tokenade), **changing
how a tool is set up is done only through its manifest, via PR** — never by
special-casing in the harness. That is the mechanism that keeps the board
impartial. Maintainers of any measured tool are explicitly invited to correct
their own entry.

## Fix or add a competitor

Each competitor is one directory under `competitors/<name>/` with a
`manifest.json`. Fields:

| field | meaning |
|-------|---------|
| `verified` | `true` only once the install steps run cleanly on a fresh machine. `false` stubs refuse to run without `--allow-unverified`. |
| `install_doc` | the upstream README step(s) followed, verbatim, with a link. |
| `version_pin`, `version_checked` | exact version measured + the date it was checked. |
| `requires` | binaries that must be on `PATH` **before** the run (checked before `setup_commands`). |
| `setup_commands` | per-run commands executed inside the sandbox workspace; their wall time is recorded as `setup_ms` (so indexing/build cost is counted). |
| `mcp` | the MCP server entry, transcribed verbatim from what the tool's own installer writes. |
| `settings` | Claude Code settings the tool installs (e.g. `hooks`). |
| `config_files` / `home_files` | files the installer drops in the config dir / HOME (e.g. a license key). |
| `tool_prefixes` / `bash_command_markers` | how the harness counts the tool's own invocations (adoption). |

Rules:

1. **Follow the upstream README, nothing custom.** Install exactly as a real
   user would. If the installer is invasive (writes outside the sandbox), do
   **not** run it in the harness — transcribe the MCP/hook entries it would
   write and let the harness inject them.
2. **No external paid dependencies assumed.** A tool that needs an API key or a
   hosted service the harness doesn't provision is marked `operational:false`
   and excluded from the ranking (with a note), not silently scored as control.
3. **Pin versions.** Reproducibility requires an exact `version_pin`.

Validate locally before opening a PR:

```bash
bash setup/install_competitors.sh        # host binaries
python3 fixtures/generate_fixtures.py     # deterministic fixtures
python3 runner.py selftest                # verifiers must PASS
python3 runner.py run -c <name> -t doc-digest --reps 1 --allow-unverified
```

## Add or change a task

Tasks live under `tasks/<id>/` (`task.json`, `prompt.md`, `verify.py`). The
task set is **frozen before a campaign** and never tuned to flatter or punish a
tool. A verifier must score 0–1 from ground truth that is **never present in
the workspace**, and must award no credit on an empty workspace
(`runner.py selftest` enforces this). New tasks land before the next campaign,
not mid-run.

## Reporting results

Run on a **single** Claude Code version (`leaderboard.py` warns on mixed
versions), `--reps 3` minimum, then `python3 leaderboard.py`. All raw per-run
data (`docs/data/results.json`) and unfavorable results — including tokenade's —
are published unedited.
