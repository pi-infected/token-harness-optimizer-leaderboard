# Publishing THOL (repo + public leaderboard site)

The benchmark runs locally; only the **results and the static site** go public.
Nothing here is automated by the agent — these are the GitHub steps you run
yourself (the agent will not push or make anything public without your go-ahead).

## 1. Create the public repo and push

```bash
cd ~/.cursor-tutor/projects/token-harness-optimizer-leaderboard

# option A — GitHub CLI (recommended)
gh repo create thol --public --source=. --remote=origin \
  --description "Token-Harness Optimizer Leaderboard — reproducible end-to-end benchmark"
git push -u origin main

# option B — web UI: create an empty public repo named e.g. "thol", then:
# git remote add origin git@github.com:<you>/thol.git
# git push -u origin main
```

What gets published is exactly what is committed (run `git ls-files` to see it):
harness, manifests, tasks, verifiers, `setup/install_competitors.sh`, the
README, the static site in `docs/`, and the dataset `docs/data/results.json`.
Excluded by `.gitignore`: caches, per-run transcripts, the sqlite DB and its
backups, logs, and all agent-instruction files (CLAUDE.md/AGENTS.md/etc.).

## 2. Enable GitHub Pages (GitHub Actions source)

Repo **Settings → Pages → Build and deployment → Source: "GitHub Actions"**.

The workflow `.github/workflows/pages.yml` is already in the repo. It deploys
the `docs/` folder on every push to `main` that touches `docs/**`. After the
first push, trigger it once via **Actions → "Deploy leaderboard to GitHub
Pages" → Run workflow**, or just push any `docs/` change.

The site will be served at `https://<you>.github.io/thol/`.

## 3. One link to update after you know the URL

- `docs/index.html` — the "Full method & reproduction steps" link currently
  points at `https://github.com/`; set it to your repo URL.
- `README.md` — optionally add the live site URL near the top.

## 4. Refreshing results later

Re-running the campaign updates `docs/data/results.json`:

```bash
python3 runner.py run -c all -t all --reps 3   # or a subset
python3 leaderboard.py                          # rewrites docs/data/results.json + leaderboard.md
git add docs/data/results.json && git commit -m "results: refresh" && git push
```

Pages redeploys automatically on push. The site reads the JSON at load time, so
no rebuild step is needed.
