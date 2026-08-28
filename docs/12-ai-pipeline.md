# AI Pipeline (GitHub Actions + OpenCode Zen)

This repository's AI features are split across two repos:

- **[lorenzogirardi/ci-shared](https://github.com/lorenzogirardi/ci-shared)** (tag `@v1`) — the reusable
  workflows and Python scripts. Also used by other repos (e.g. `cloudflare-free-exporter`), so a fix
  here benefits every consumer.
- **this repo** — thin wrapper workflows that call `ci-shared@v1` with this project's own config
  (prompts, gates, secrets), plus two workflows that don't fit the reusable shape and call the
  shared scripts directly.

Model calls go through one stdlib-only client, `openrouter_ai.py`, checked out from `ci-shared` at
run time (never duplicated locally). No Claude API, no Claude Code routines — a plain HTTP call to
any OpenAI-compatible chat-completions endpoint.

## Six features, six workflows

| # | Feature | Workflow | Trigger | Merges/blocks anything? |
|---|---------|----------|---------|--------------------------|
| 1 | Deterministic pre-merge gate | `pr-checks.yml` | `pull_request` | **Yes** — required check for auto-merge |
| 2 | AI code review (human PRs) | `ai-review.yml` | `pull_request`, skips `renovate[bot]` | No — comment only |
| 3 | Renovate review, auto-merge, self-repair | `ai-review-sweep.yml` | `schedule` (2×/day) + `workflow_dispatch` | **Yes** — see below |
| 4 | Post-pipeline security/quality report | `pipeline.yml` → `ai-analysis` job | `push` to `main` | No — job summary + artifact |
| 5 | Automatic issue triage | `issue-triage.yml` | `issues` (opened), `bug`-labeled | No — labels/comment only |
| 6 | Automatic release notes | `release-notes.yml` | `pull_request` (closed, merged) | No — comment only |

Features 2 and 3 are split by actor because they need different privileges (see "Why two review
workflows" below) — never both on the same PR.

## Why `pr-checks.yml` exists, and why it's required

Until this existed, `pipeline.yml` only ran `on: push: [main]`: nothing was ever built or tested on
a PR, so the first `pytest` of a change happened *after* it had already landed. Two auto-merged
dependency bumps broke `main` in one session because of exactly that gap — both failures a command
proves in seconds, neither something a diff review can predict:

- Python 3.12 → 3.14 made `pip install -r requirements.txt` unsolvable (`mcp` needs
  `pydantic>=2.12` on 3.14; `requirements.txt` pinned `2.11.7`) — a `pip install --dry-run` would
  have caught it immediately.
- `fastapi` 0.115 → 0.141 made every request 500 (`prometheus-fastapi-instrumentator` 7.0.2 can't
  read the new router objects) — booting the app and hitting `/api/mgmt/ready` once would have
  caught it immediately.

`pr-checks.yml` runs on every PR: dependency resolution (its own step, so a resolver conflict is
legible — and *without* `--quiet`, since that flag hides pip's "The conflict is caused by:" block,
the only part naming the actual incompatible pins), lint, `pytest`, and a smoke test that boots
`uvicorn` and requests `/api/mgmt/ready` / `/api/mgmt/health` / `/metrics` — the path the test
suite itself can't cover, since `tests/conftest.py` sets `PROMETHEUS_ENABLED=false` for the whole
suite. Also runs `actionlint` on every workflow file (job name: `workflows`), which caught a real
latent bug on its first run: a `docker/build-push-action` step with no `id`, silently making
`steps.docker_build.outputs.digest` resolve to nothing.

Heavy jobs (multi-arch docker build, trivy, sbom, kind cluster) stay in `pipeline.yml` on `main` —
too slow to run per PR.

## Why two review workflows, gated by actor

This repo's dependency bot is **Renovate** (`renovate.json`), not Dependabot — confirmed the hard
way: enabling native Dependabot alongside it produced 12 duplicate PRs for updates Renovate already
tracked. Cleaned up; `.github/dependabot.yml` was removed.

`ai-review.yml` (`pull_request`, `contents: read`) handles everything **except** `renovate[bot]`.
`ai-review-sweep.yml` (`schedule` + `workflow_dispatch`, `contents: write`) handles only
`renovate[bot]`, with a dependency-bump-focused prompt and the merge/autofix capability described
below.

### Why the Renovate path is a *sweep*, not another `pull_request` trigger

The event-driven approach was tried first and works, but needed a real fight to get there:
`pull_request` gives a read-only `GITHUB_TOKEN` and no secrets to runs authored by a bot (this
turned out **not** to be Dependabot-specific — `renovate[bot]` hit the identical restriction),
`pull_request_target` (the usual escape hatch) defaults to checking out the *base* branch instead
of the PR, and a workflow added today can never retroactively fire for PRs opened yesterday.

A `schedule` run has none of that: no PR actor, no fork, full `GITHUB_TOKEN` by construction. It
also mirrors how [`openwrt/openwrt`](https://github.com/openwrt/openwrt) actually drives its own
LLM review (`cron '0 3,15 * * *'` + `workflow_dispatch`, no `pull_request` trigger at all — verified
by reading its real workflow file, not assumed).

### The merge gate: CI, not the AI verdict

Auto-merge requires `required_checks: 'checks,workflows'` (the `pr-checks.yml` job names) to have
**actually succeeded** — not merely "nothing failed". An earlier version accepted that weaker
condition and merged two PRs whose only check was `ai-review.yml` reporting `skipped` (it skips bot
authors): "nothing objected" is not "something verified". The AI review's `VERDICT: CLEAN` /
`VERDICT: NEEDS_REVIEW` line (exact-match on the literal last line, not a substring search — a
model writing "no `[Critical]` issues found" to mean *clean* must not read as dirty) only decides
whether a human needs to look; it has never been the thing that decides whether code merges.

### Why GitHub Actions version bumps don't merge through the sweep at all

A PR that bumps a pin inside `.github/workflows/*.yml` (e.g. `docker/setup-buildx-action@v4.2.0` →
`@v4.3.0`) produces a merge commit that changes the content of a workflow file — and GitHub gates
*that*, specifically, behind the `workflow` OAuth scope, regardless of any `permissions:` a job
declares. `GITHUB_TOKEN` never has it, so the sweep's `touches_workflow_files()` refuses the merge
outright rather than let GitHub reject it with a confusing API error after a clean review and green
CI (which is exactly what happened on PRs #103/#105/#107/#114 before that check existed).

These PRs auto-merge through **Renovate's own automerge** instead (`renovate.json`,
`packageRules` → `matchManagers: ["github-actions"]`), which uses Renovate's own GitHub App
credentials — already granted `workflow`-equivalent permission at install time — and still waits
for `checks`/`workflows` from `pr-checks.yml` to pass first. The AI sweep bot gains no extra scope;
it still only ever pushes/merges within `Contents: Read and write` on this one repo.

### Self-repair: agentic autofix on a failing PR

When Renovate's own PR fails `pr-checks.yml`, the sweep doesn't just explain the failure — it can
repair it, `autofix: true`:

1. Read the failing job's logs (de-ANSI'd; `gh api` silently refuses colored output without
   `--allow-escape-sequences`) and the PR diff.
2. Ask the model for a patch: strict JSON, `{"file", "find", "replace"}` pairs. Every edit is
   validated in code, not trusted from the prompt — `find` must appear **exactly once** in that
   file, at most 5 edits, no path traversal, never on a fork. No file-type restriction beyond
   that: a major bump can break at the API level, not just at install time (real incident below),
   and a pin revert can't fix that — only a code change can. The one hard exclusion is
   `.github/workflows/**`, which no credential here can push regardless (needs the separate
   `workflow` scope), so an edit there would just burn the attempt.
3. Apply the edit, then run `verify_command` **in this job**, before pushing anything — this is
   what makes it agentic rather than one-shot: the model finds out whether its own fix works
   locally, the same way fixing this class of bug interactively does (propose → check the real
   output → adjust), instead of only discovering it a full CI round trip later.
   `verify_command` here re-runs `pr-checks.yml`'s own steps verbatim (resolve → install → lint →
   **pytest** → boot → curl) on `python_version: "3.14"` — lint and the real test suite are in it,
   not just install/boot, because a code-level fix needs the real test suite to mean anything;
   matching the real gate's interpreter is not optional either — a dependency set can resolve on
   one Python version and not another, which is literally how the incident above happened.

   **Real incident, code-level**: Renovate's `mcp` v1→v2 bump broke `app/mcp/tools.py` at import
   time (`ModuleNotFoundError: No module named 'mcp.server.fastmcp'` — v2 renamed `FastMCP` to
   `MCPServer`). Autofix is deliberately allowed to fix the call site itself here, not just revert
   the pin — reverting would only make Renovate re-propose the identical bump forever, since it has
   no way to know the bump was tried and rejected. First attempt renamed the import correctly (the
   error message named the new class) but guessed the constructor's new keyword argument wrong —
   nothing in the error mentioned it, and the model had no way to check. Second attempt fell back
   to a revert, which is what actually merged on PR #117 — see the
   [full case study](case-study-mcp-v2-autofix.html) for every prompt and log involved.

   **`list` / `find` / `grep` / `read`**: a reply can explore before proposing an edit — list a
   directory, find a file by name, grep file contents, or read one real file (this repo, an
   installed package, or the standard library) — instead of guessing an API or a runner-specific
   absolute path from an error message alone. Added incrementally as the same PR (#118, Renovate
   reopens the identical bump every time a prior attempt reverts it — it has no memory of a
   rejected bump) kept exposing the next gap: `read` alone still needs an exact path, which the
   model guessed wrong (a plausible but non-matching toolcache path); dotted-module resolution and
   `find`/`grep`/`list` close that. Then a real run with all four available spent all 5 rounds on
   distinct, useful exploration (tools.py → the renamed class → its own submodule → the call site →
   grepping for the old kwarg) and had zero rounds left to actually propose a fix — each of these
   costs a round like a proposed edit does, so `max_autofix_attempts: 8` here, not the default 3.
4. A pass commits (with an explicit git identity — a runner checkout has none) and pushes
   immediately, with a commit message and PR comment stating plainly that a machine wrote it,
   unreviewed, and that the required checks (the real ones, on the pushed commit) decide whether it
   merges. A failure reverts the edit, feeds the real verification output back into the next
   attempt ("tried X, still failed with Y"), and retries — up to `max_autofix_attempts` (default 3)
   — before giving up and leaving the PR for a human.

Verified end to end on a deliberately broken PR: one attempt, verified locally, pushed, and the
real `pr-checks.yml` run on that commit came back green — confirming the local verifier and the
actual gate agree.

**Where the LLM is used, and where it deliberately isn't**: if a command can prove something, ask
the command, not the model — a diff review calling a resolvable-on-py3.12-but-not-py3.14 dependency
bump "clean" is exactly the failure mode this whole design routes around. The model's job is
triage/explanation (something already proven wrong, in one attempt) and generating a candidate fix
whose correctness is then decided the same way any other commit's is: by CI.

## Architecture

```
GitHub Actions ──► ci-shared/scripts/openrouter_ai.py ──► OpenCode Zen (opencode.ai/zen/v1)
   (checked out          (stdlib only)                        model: hy3-free
    at run time,                                          (deepseek-v4-flash-free went
    ref: v1)                                                unavailable; verified via
                                                             direct curl before switching)
```

- `openrouter_ai.py` — reusable client: reads key/model/endpoint from the environment, accepts a
  multiline prompt from a file, validates response JSON, retries on an empty reply (reasoning
  models can burn the whole output budget on chain-of-thought), caps prompt size, never prints
  secrets. Writes token usage + an estimated USD cost.
- `ai_sanitize.py` — redacts secrets and caps size of CI output before it reaches the model; masks
  secret-like patterns in a finished report before upload (never drops the whole report just
  because it quotes a `password = "..."` line while explaining a vulnerability).
- `ai_append_cost.py` — appends a token/cost footer to a report.
- `pr_review_sweep.py` — the sweep's own logic: `checks_state()` (the merge gate), `triage_one()`,
  `autofix_one()` (the agentic loop above), verdict parsing. 63 tests in `ci-shared`, no network.

Full design rationale, Mermaid diagrams, and the file-by-file breakdown live in
[`ci-shared/docs/architecture.md`](https://github.com/lorenzogirardi/ci-shared/blob/main/docs/architecture.md).

## GitHub Configuration

### 1. API key (secret)

```bash
gh secret set OPENROUTER_API_KEY --repo lorenzogirardi/flask-test-api --body 'sk-or-...'
```

The key is only ever used in the `Authorization: Bearer` header — never logged, never in a prompt,
never uploaded as an artifact.

### 1b. Autofix push token (secret, optional)

Without this, autofix's `git push` authenticates as `GITHUB_TOKEN`, and GitHub's own
recursive-workflow guard silently suppresses the `pr-checks.yml` run that push would otherwise
trigger — confirmed live on PRs #104 and #110, both stuck forever with a `action_required`,
zero-job run on the pushed commit. Required checks can then never go green, so the PR can never
merge, regardless of how good the fix was.

Create a **fine-grained PAT**, repository access limited to `flask-test-api` only, permission
**Contents: Read and write** and nothing else (never `workflow` scope — this token must not be
able to touch `.github/workflows/**`, which stays a human-merge-only path on purpose):

```bash
gh secret set AUTOFIX_PUSH_TOKEN --repo lorenzogirardi/flask-test-api --body 'github_pat_...'
```

Unset, `ai-review-sweep.yml` falls back to `GITHUB_TOKEN` exactly as before — autofix still
proposes and verifies fixes locally, it just can't get real CI to confirm them.

### 2. Model (variable)

Current: **`hy3-free`** (the previous default, `deepseek-v4-flash-free`, started returning
`Model is unavailable` from the provider — verified with a direct `curl` against the endpoint
before switching, not assumed).

```bash
gh variable set OPENROUTER_MODEL --repo lorenzogirardi/flask-test-api --body 'hy3-free'
```

### 3. Referrer / App name (variables, optional)

```bash
gh variable set OPENROUTER_SITE_URL --repo lorenzogirardi/flask-test-api --body 'https://github.com/lorenzogirardi/flask-test-api'
gh variable set OPENROUTER_APP_NAME --repo lorenzogirardi/flask-test-api --body 'GitHub Actions AI'
```

### 4. Enable / disable

```bash
gh variable set AI_ENABLED --repo lorenzogirardi/flask-test-api --body 'true'   # enable
gh variable set AI_ENABLED --repo lorenzogirardi/flask-test-api --body 'false'  # disable
```

When `AI_ENABLED != 'true'`, every AI job is skipped; `pr-checks.yml` (deterministic, no model
call) is **not** gated by this variable and always runs.

### 5. Required GitHub permissions

| Workflow | Permissions | Why |
|----------|-------------|-----|
| `pr-checks.yml` | `contents: read` | no model call, no comment |
| `ai-review.yml` | `contents: read`, `pull-requests: write` | post/update review comment |
| `ai-review-sweep.yml` | `contents: write`, `pull-requests: write` | merge + push autofix commits |
| `pipeline.yml` (`ai-analysis`) | `contents: read`, `actions: read` | download/upload artifacts |
| `issue-triage.yml` | `issues: write`, `contents: read` | labels + comment |
| `release-notes.yml` | `contents: read`, `pull-requests: write` | post comment |

No workflow requests `write-all`.

### 6. Branch protection

**Deliberately not enabled** on `main`. Reasons: `pipeline.yml`'s `modifygit` job pushes directly
to `main` (the image-tag bump after each build) and would break under "require PR before merging";
the merge gate that matters (`required_checks`) already lives in the sweep, not in GitHub's branch
protection; and the owner pushes to `main` directly as a matter of workflow. If this changes, the
sweep's `required_checks` list is what a branch protection rule should mirror.

### 7. Local validation

```bash
pytest tests/ -v                                          # this repo's own suite
pytest ../ci-shared/tests/ -v                              # or wherever ci-shared is checked out
echo 'Say hi' | OPENROUTER_API_KEY='sk-or...' python3 -c "..."  # smoke test, not required for CI
```

### 8. Fork pull requests

`ai-review.yml` (plain `pull_request`) blanks the API key on a fork PR before ever calling the
model — untrusted fork code never gets a real key, and the review comment reports that AI review
did not run. `ai-review-sweep.yml` never runs against a fork at all: it only processes PRs whose
`head.repo.full_name` equals this repo, checked before any git operation.

## Security notes

- Prompts exclude `.env`, keys/certificates, `.git`, `node_modules`, `vendor`, `dist`, `build`,
  minified maps, and binary assets.
- All prompt content (diffs, issue bodies, PR titles, CI logs) is treated as untrusted data; system
  prompts instruct the model to ignore embedded instructions. Model output is never executed as
  shell commands directly from the prompt — the autofix path parses it into a strict schema first
  (see "Self-repair" above) and validates every field before it touches a file.
- Generated reports are scanned for secret patterns before upload; matches are masked, not silently
  dropped.
- The autofix's `pull_request_target`-adjacent risk (arbitrary code execution from a PR branch with
  an elevated token) does not apply here: the sweep only ever reads PR content (diff, logs) to build
  a prompt, and writes are validated in code (`parse_fix`/`apply_fix`) before anything reaches disk
  — unique-anchor edits, all-or-nothing, never to `.github/workflows/**` (the one hard exclusion; see
  `case-study-mcp-v2-autofix.html` and `ci-shared/docs/architecture.md` for why edits are no longer
  restricted to dependency manifests beyond that). `verify_command` does run the PR branch's own code
  for real (pytest, boot) — that's the point, a real test suite is what gates a wrong fix — but it
  runs with the same token scope regardless of what file was touched, never an elevated one.
- `.ai/` (the jobs' working directory) is gitignored and never committed.
