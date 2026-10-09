# AI Pipeline (GitHub Actions + OpenRouter)

> **Superseded in part.** The `ai-autofix-main` job (a PR to repair a red `main`) was removed: a red `main` is now taken back to the last green state by `agent-main-guard.yml`, which says so on the pull request the change came from; nothing is redone automatically. The sweep's CI repair uses the same engine as everything else.
>
> **Also superseded.** `ai-review.yml` was removed: every non-Renovate PR, and every direct push to `main`, now goes through `agent-change.yml`. The sweep is back to Renovate PRs only. The sections below that describe `ai-review.yml` or "Autofix now covers the owner's own PRs too" describe the previous setup.
>
> The role-based agent pipeline (writer, reviewers, failure adjudicator, test steward, changelog), its health check and its canary, and the move to `ci-shared` `v2` are described in [13-agent-pipeline.md](13-agent-pipeline.md). **That document is the current description; this one is kept for the reasoning behind the older workflows.**

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

## Seven features, seven workflows

| # | Feature | Workflow | Trigger | Merges/blocks anything? |
|---|---------|----------|---------|--------------------------|
| 1 | Deterministic pre-merge gate | `pr-checks.yml` | `pull_request` | **Yes** — required check for auto-merge |
| 2 | AI code review (human PRs) | ~~`ai-review.yml`~~ → `agent-change.yml` | `pull_request`, skips `renovate[bot]` | Reviews, pushes fixes to the PR branch and certifies; `agent-merge.yml` merges a certified, green commit (see [13](13-agent-pipeline.md)) |
| 3 | Sweep: review + self-repair (Renovate and the owner), auto-merge (Renovate only) | `ai-review-sweep.yml` | `schedule` (2×/day) + `workflow_dispatch` | **Yes**, but only for `renovate[bot]` — see below |
| 4 | Post-pipeline security/quality report | `pipeline.yml` → `ai-analysis` job | `push` to `main` | No — job summary + artifact |
| 5 | Self-repair on a direct push to `main` | ~~`pipeline.yml` → `ai-autofix-main`~~ → `agent-main-guard.yml` (re-run once, then revert) | after `Python application` fails on `main` | **Yes** — reverts `main` to the last green state |
| 7 | Automatic release notes | `release-notes.yml` | `pull_request` (closed, merged) | No — comment only |

Features 2 and 3 are split by actor for the *review* prompt (dependency-bump-focused vs.
general-purpose) because they need different privileges to run at all (see "Why two review
workflows" below) — but feature 3's self-repair, specifically, no longer implies feature 3's
auto-merge: see "Autofix now covers the owner's own PRs too" below.

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

`ai-review.yml` (`pull_request`, `contents: read`) handles everything **except** `renovate[bot]`,
review only, no autofix. `ai-review-sweep.yml` (`schedule` + `workflow_dispatch`,
`contents: write`) reviews and repairs `renovate[bot]` **and** the repo owner's own PRs
(`authors: 'renovate[bot],lorenzogirardi'`), with a dependency-bump-focused prompt — but
`auto_merge_authors: 'renovate[bot]'` means only Renovate's PRs are ever merged unattended; the
owner's get a verified fix pushed to the same PR, same as Renovate's, and then wait for the owner
to merge. See "Autofix now covers the owner's own PRs too" below.

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
   `find`/`grep`/`list` close that. A run with all four available at 8 rounds got real,
   self-correcting progress — explored the renamed class, proposed a plausible constructor fix,
   learned from its own failed verification, refined it, kept exploring (the last grep, 27 hits on
   `streamable_http_app`, points at `app/main.py`'s ASGI mount needing an edit too) — but exhausted
   before landing a passing fix, a multi-file migration needing more rounds than that. Each
   exploration step costs a round like a proposed edit does, so `max_autofix_attempts: 20` here.
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

### Autofix now covers the owner's own PRs too

The gap this closes: a PR opened by the repo owner (not Renovate) got `ai-review.yml`'s diff
comment and `pr-checks.yml`'s pass/fail, but nothing ever repaired a red run on it — the sweep's
`authors` filter excluded anyone but `renovate[bot]`. `ai-review-sweep.yml` now sweeps
`renovate[bot],lorenzogirardi`, so the exact same propose→verify→push loop described above also
runs on the owner's red PRs.

What's deliberately unchanged is *who gets merged unattended*: `auto_merge_authors: 'renovate[bot]'`
means `try_merge()` is never called for anything the owner opened, clean review or not, fixed or
not — the fix lands on the PR branch the same way Renovate's does, but a human merges it. This is
`ci-shared`'s `auto_merge_authors` input (see its `docs/architecture.md`), not a
`flask-test-api`-specific gate: `authors` (who gets reviewed/autofixed) and `auto_merge_authors`
(who gets merged) are now two separate knobs, where they used to be the same one.

### Self-repair on a direct push to `main`

The other gap: a push straight to `main` (not through a PR at all) that breaks `build` or
`k8s-check` got **zero** repair attempt — `ai-analysis` (feature 4) only reports, and the sweep
(feature 3) only ever looks at open PRs, which a direct push to `main` doesn't create. `pipeline.yml`'s
new `ai-autofix-main` job, `needs` the same job list `ai-analysis` does but runs only when `build` or `quality-gate` failed (the gates `verify_command` can reproduce) instead
of `if: always()`, closes it — using `ci-shared`'s `reusable_main-autofix.yml` (see its
`docs/architecture.md` for the full design).

It deliberately does **not** push a fix to `main` directly, even though `modifygit` already does
exactly that for the image-tag bump (see "Branch protection" below) — a verified-fix commit and a
mechanical, idempotent tag bump are not the same risk. Instead it checks out a new branch from the
broken commit, runs the same autofix loop, and on a verified fix opens a **new PR** with it — which
then goes through `pr-checks.yml` like any other PR, and can be picked up by the next sweep run.
Nothing here merges anything; a broken `main` build gets, at best, a candidate fix waiting for a
human (or the sweep) to land it, never an unattended change to `main` itself.

This is also the one place `AUTOFIX_PUSH_TOKEN` (see "1b" above) is closer to required than
optional: `gh pr create` under `GITHUB_TOKEN` still opens the PR, but GitHub's recursive-workflow
guard suppresses the `pull_request: opened` event for it, so `pr-checks.yml` never runs — the PR
sits there looking like any other idle PR, with no signal that its checks never fired at all.

## Architecture

```
GitHub Actions ──► ci-shared/scripts/openrouter_ai.py ──► OpenRouter (openrouter.ai/api/v1)
   (checked out          (stdlib only)                        model: ~deepseek/deepseek-v4-flash-latest
    at run time,                                          (router alias — resolves to the current
    ref: v1)                                                DeepSeek V4 Flash; not a free tier)
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
  `autofix_one()`, `may_auto_merge()` (the `auto_merge_authors` gate), verdict parsing.
- `autofix_core.py` — the propose/explore/verify/retry loop itself, a small langgraph graph shared
  by `autofix_one()` and `main_autofix.py` (see below); everything else in `ci-shared` stays
  stdlib-only.
- `main_autofix.py` — the direct-push-to-`main` path: no PR to look failures up through or push a
  fix to, so it opens a new one instead. 118 tests total in `ci-shared`, no network.

Full design rationale, Mermaid diagrams, and the file-by-file breakdown live in
[`ci-shared/docs/architecture.md`](https://github.com/lorenzogirardi/ci-shared/blob/main/docs/architecture.md).

## GitHub Configuration

### 1. API key (secret)

```bash
gh secret set OPENROUTER_API_KEY --repo lorenzogirardi/flask-test-api --body 'sk-or-v1-...'
```

Get the key from <https://openrouter.ai/keys>.

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

The same secret is wired into `pipeline.yml`'s `ai-autofix-main` job too, where it is closer to
load-bearing than optional: that job opens a brand-new PR via `gh pr create`, and under plain
`GITHUB_TOKEN` the `pull_request: opened` event for that PR is suppressed the same way a
`synchronize` push is — the PR appears, `pr-checks.yml` never runs on it, and nothing surfaces
that silently. Unset, the PR still opens, but treat it as needing a manual `pr-checks.yml` trigger
before trusting it.

### 2. Model + endpoint (variables)

Current: **`~deepseek/deepseek-v4-flash-latest`** on **OpenRouter** (`https://openrouter.ai/api/v1`).
The `~` prefix marks an OpenRouter router alias — it resolves to the current DeepSeek V4 Flash
snapshot, so the pin doesn't go stale when a dated snapshot is retired (the recurring failure mode
on the old OpenCode Zen free models: `hy3-free` / `deepseek-v4-flash-free` each went
`Model is unavailable` without notice). This model is **not** a free tier — calls cost tokens;
`openrouter_ai.py` writes the per-run USD estimate to the job summary.

```bash
gh variable set OPENROUTER_ENDPOINT --repo lorenzogirardi/flask-test-api --body 'https://openrouter.ai/api/v1/chat/completions'
gh variable set OPENROUTER_MODEL --repo lorenzogirardi/flask-test-api --body '~deepseek/deepseek-v4-flash-latest'
```

To browse alternatives: `GET https://openrouter.ai/api/v1/models` (add `?supported_parameters=...`
to filter). Any OpenAI-compatible chat-completions endpoint works here — only these two variables
and the API key change.

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
| `agent-change.yml` | `contents: read`, `pull-requests: write` (+ `AUTOFIX_PUSH_TOKEN` in the publish step only) | review comment, fix commits on the PR branch |
| `ai-review-sweep.yml` | `contents: write`, `pull-requests: write` | merge + push autofix commits |
| `pipeline.yml` (`ai-analysis`) | `contents: read`, `actions: read` | download/upload artifacts |
| `agent-main-guard.yml` | `contents: read`, `actions: write` (+ `AUTOFIX_PUSH_TOKEN` to revert) | re-run a failed job once; revert the culprit |
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
