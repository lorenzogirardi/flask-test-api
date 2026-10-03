# Agent pipeline (ci-shared v2)

Role-based agents that take an issue to a reviewable pull request, plus a
changelog step and a documentation architect. The roles and the code that acts
on their output live in `ci-shared` (tag `v2`), so other repositories can reuse
them. This repository only wires them up. For the older single-purpose AI
workflows see [12-ai-pipeline.md](12-ai-pipeline.md).

## What runs when

| Change | Workflow | What happens |
|---|---|---|
| Issue labelled `agent` (or run by hand) | `agent-pipeline.yml` | Full pipeline from the request: planner, writer, checks, reviewers, fix loop, final review, docs, changelog, PR. |
| Any pull request except Renovate's | `agent-change.yml` (job `pull-request`) | No planner (the author's description is the intent). Checks, reviewers A and B, fix loop that **pushes fix commits to the PR branch**, final review, docs review. One comment on the PR, edited on every run. |
| Push straight to `main` with no PR | `agent-change.yml` (job `direct-push`) | Same review. If something blocks it opens a fix PR from `agent/push-<sha>` (never pushes to `main`); otherwise it leaves a commit comment with the advisory findings. |
| Renovate PRs | `ai-review-sweep.yml` | Unchanged: its own review, autofix and auto-merge. |
| Every push to `main` | `changelog.yml` | One deterministic entry. |

Two guards stop loops and noise: every commit the pipeline makes has the author
`ci-shared agents`, and a run whose head commit has that author does nothing; a
push whose commit belongs to a PR is skipped, because the PR was reviewed.
A change the agent did not alter is certified by the first review alone, with
no extra calls. Pushes to a PR branch are made with `AUTOFIX_PUSH_TOKEN`, so the
PR checks re-run on them.

## How to run the issue pipeline

1. Create an issue that describes the change.
2. Add the label `agent` (or run the workflow **Agent Pipeline** by hand with
   the issue number).
3. Follow the run in Actions. The result is a comment on the issue and a pull
   request from the branch `agent/issue-<n>-<run>`.

Nothing is merged automatically. If the loop did not converge, the PR is a
**draft** titled `[needs human]` and lists the findings still open.

Required: variable `AI_ENABLED=true`, variable `OPENROUTER_MODEL`
(`deepseek/deepseek-v4.1-flash`), secret `OPENROUTER_API_KEY`, and secret
`AUTOFIX_PUSH_TOKEN` with **Contents and Pull requests** read/write on this
repository (never `workflow` scope). A pull request opened as `GITHUB_TOKEN`
would not trigger PR Checks, so the workflow refuses to publish without it.

## What happens

| Step | Role | Notes |
|---|---|---|
| 1 | Planner | Reads the issue and the repository, writes scope, out-of-scope and acceptance criteria. Never edits code. May stop with "not feasible" and say what is missing. |
| 2 | Writer | Implements the change and its tests inside the plan: at most 8 changes per turn, unique-anchor edits or new files, never `.github/workflows/`. |
| 3 | Deterministic checks | Same steps as `pr-checks.yml` (dependency resolution, install, lint, tests, smoke test). Run after every change. A failure is reverted and fed back to the writer. |
| 4 | Reviewer A | Correctness and design, against the plan. |
| 5 | Reviewer B | Security and operability. Does not see reviewer A's output. |
| 6 | Dedup and validation | Findings need severity, file, line, evidence and a fix. A finding whose line is not in a changed hunk is dropped. Findings about the same place and topic are merged. |
| 7 | Fix loop | Blocking findings (`critical`, `high`) go back to the writer; then steps 3 to 6 run again. At most `max_iterations` (3) rounds. |
| 8 | Final reviewer | Checks the blocking findings are really fixed and looks for regressions. |
| 9 | Documentation reviewer | Edits only documentation files, only when the diff justifies it, then re-runs the checks. |
| 10 | Changelog | A deterministic entry in `CHANGELOG.md` unless the change already has one. |

All agents use the model in `OPENROUTER_MODEL`. Independence between reviewers
comes from separate calls, different prompts and no shared context, not from
different models.

## Credential boundaries

- The step that runs the agents has the model key and **no write token**.
- The deterministic checks run in a process whose environment is an allow-list
  (no model key, no token), from a checkout that keeps no credentials. The code
  under test was written by a model moments ago; `pip` and `pytest` execute it.
- Only the last step (`publish`) holds the write token, and it runs no code from
  the repository.

## Changelog

`changelog.yml` adds one entry to `CHANGELOG.md` for every push to `main`, from
the commit subject (a squash merge uses the PR title). It does not use a model.
It skips the pipeline's own commits (`Done by Github Actions…`, `docs(changelog)…`)
and any commit that already changed `CHANGELOG.md`. Re-running it never
duplicates an entry.

## Documentation architect

The **Docs Architect** workflow (manual) classifies each document as tutorial,
how-to, reference or explanation (Diataxis), lists gaps found from the code,
and proposes a directory structure and navigation map. It is plan-only: the run
fails if any file changes. Proposed new documents need evidence from the
repository, and each gap says whether it can be verified from the code or needs
a person. Later changes must come as a patch or PR reviewed by a person. The
changelog is out of its scope.

## Limits and known gaps

- The loop is bounded: `max_iterations` review rounds, `max_verify_retries`
  failed-check retries, `writer_rounds` turns per attempt.
- A reviewer that returns no usable reply stops the run and escalates; nothing
  is certified by default.
- Cost per role is recorded in the run artifact (`agent-run-<issue>`) and shown
  in the PR.
- The direct-push mode can only react after the push; it cannot stop it.
  Checks that fail on `main` itself are handled by `ai-autofix-main`.
- `reusable_agent-review.yml` (reviewers only, no fixes) exists in `ci-shared`
  but is not wired to a trigger here.
