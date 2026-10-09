# Agent pipeline (ci-shared v2)

Role-based agents that review, repair, certify and merge every pull request, plus a
changelog step and a documentation architect. The roles and the code that acts
on their output live in `ci-shared` (tag `v2`), so other repositories can reuse
them. This repository only wires them up. For the older single-purpose AI
workflows see [12-ai-pipeline.md](12-ai-pipeline.md).

## What runs when

| Change | Workflow | What happens |
|---|---|---|
| Any pull request except Renovate's | `agent-change.yml` (job `pull-request`) | No planner (the author's description is the intent). Checks, reviewers A and B, fix loop that **pushes fix commits to the PR branch**, final review, docs review. One comment on the PR, edited on every run. |
| `PR Checks` fails on a PR (not Renovate's) | `agent-ci-failure.yml` | The failing checks' real logs are the first input, including `integration`. Each failing test gets a verdict (below) before anything changes. Fixes are pushed to the PR branch; it stops after 3 consecutive agent commits that still fail CI. |
| Push straight to `main` with no PR | `agent-change.yml` (job `direct-push`) | Same review. If something blocks it opens a fix PR from `agent/push-<sha>` (never pushes to `main`); otherwise it leaves a commit comment with the advisory findings. |
| Renovate PRs | `ai-review-sweep.yml` | Starts by itself when a PR's CI ends and when `main` moves; the cron is a safety net. A PR that fell behind `main` (counted from the commits, since this repo has no branch protection) is refreshed: Renovate is asked to rebase its own (label `rebase`), so CI runs on current code, including the `image` check. The sweep then waits for the required checks, gives the two reviewers the check results of that commit as evidence, and merges a clean PR. A blocking finding goes to the writer loop and is pushed if it converges; otherwise, or after 3 automatic fixes in a row, the PR is labelled `agent-abandoned` and closed. A PR that touches `.github/workflows/` is not reviewed or repaired (the agent token has no `workflow` scope): Renovate merges it itself once the required checks pass, and if those checks are red on current code it is labelled `agent-abandoned` and closed, so no one waits on it. |
| Every push to `main` | `changelog.yml` | One deterministic entry. |

Two guards stop loops and noise: every commit the pipeline makes has the author
`ci-shared agents`, and a run whose head commit has that author does nothing; a
push whose commit belongs to a PR is skipped, because the PR was reviewed.
A change the agent did not alter is certified by the first review alone, with
no extra calls. Pushes to a PR branch are made with `AUTOFIX_PUSH_TOKEN`, so the
PR checks re-run on them.

## Reading the Actions tab

Twelve workflows, but only three moments. Runs started by another workflow finishing (`workflow_run`) are
listed under the branch `main` by GitHub even when they are about a pull request; their title now says what
they are about (`Agent Merge · workflow_run · <pull request title>`).

| Moment | Workflows, in the order they start |
|---|---|
| A pull request is opened or updated | `PR Checks` (jobs `checks`, `integration`, `image`, `workflows`) and `Agent Change` (reviewers, fixes, certification) start together. When `PR Checks` ends: `Agent CI Failure` (repairs if red), `Agent Merge` (merges if certified and green), `AI Review Sweep` (Renovate pull requests only). After the merge: `AI Release Notes`. |
| Something lands on `main` | `Python application` builds, tests and **publishes the image** (`build`, `docker`, `security-gate-trivy`, `docker-sbom`, `quality-gate`, `modifygit` bumps the tag in `helm/pytbak/values.yaml`, `k8s-check` deploys the published image, `ai-analysis`), next to `Changelog`, `Agent Merge`, `AI Review Sweep` and `Agent Change`. When `Python application` ends red: `Agent Main Guard`. |
| Time passes | `Agent Merge` every 30 minutes and `AI Review Sweep` twice a day pick up whatever an event missed. |

Two different images are built: the `image` job of `PR Checks` builds from the pull request and never publishes it
(it proves the code becomes an image that runs); `docker` on `main` builds the same Dockerfile and publishes it.
A run that is `skipped` is a guard that decided it had nothing to do (for instance `Agent Main Guard` when `main` is
green), not a failure.

A merge must be made with the push token, not the job's `GITHUB_TOKEN`: GitHub starts no workflow for events made with
the latter, so a merge made with it would build no image, run no `k8s-check` and leave the guard blind.

## The pipeline checks itself

`pipeline-health.yml` runs every 30 minutes, with no model. It goes red, and says why in the run summary, when:

- a commit is on `main` and no `Python application` run covers it (it then starts that workflow on `main`). A merge
  made with the job's `GITHUB_TOKEN` causes exactly this, and three dependency bumps once stayed unbuilt for hours;
- a pull request was certified although an agent could not do its job (for instance the test steward's reply was
  unusable);
- one of the agent workflows ended in failure;
- a pull request is open with no verdict on its head commit (neither certified nor abandoned) and nothing has run on it
  for 90 minutes. It is then abandoned, so it never waits for a person; a new push starts a new attempt.

## The canary: known changes, checked outcomes

`pipeline-canary.yml` runs every night. For each scenario in `.github/canary.json` it opens a pull request that changes
`app/canary.py` (a module nothing imports) in a known way, against a throwaway copy of `main`. The ordinary workflows
run on it; the canary then checks facts and closes it. It is never merged.

| Scenario | The change | What must happen |
|---|---|---|
| `repair` | A bug the existing tests catch, with a vague description | The agent restores the code, the tests are not touched, the commit is certified |
| `intent` | A limit raised on purpose, said in the description, that an existing test contradicts | The test is updated, the code keeps the new limit, nothing outside `app/canary.py` and `tests/` changes, the commit is certified |
| `coverage` | A new function added with no test | The test steward adds a test for it, the function stays as written, nothing outside `app/canary.py` and `tests/` changes, the commit is certified |

The same scenarios also guard the engine itself: before `ci-shared` moves its `v2` tag to a new commit it starts this
canary in candidate mode (`repository_dispatch`), where the pull requests are judged by the engine about to be released.
The tag moves only if every scenario holds.

A red run means the agents did something else: no verdict, an abandonment, a file changed that should not be, a test
weakened. The health check reports a failed canary like any failed agent workflow.

## What to expect on your own pull request

Open a pull request from a branch as usual, with a title that says what it does (the title and description are
the agent's only statement of intent, and the changelog entry is made from the title). Nothing else is needed.

1. `PR Checks` runs the lint and unit tests, the integration suite against real PostgreSQL and Redis, the
   image built from your branch, and the workflow lint.
2. `agent-change.yml` reviews the diff with two independent reviewers. If it changes application code, the
   test steward looks at the tests. If a check fails, `agent-ci-failure.yml` reads the failing logs and decides
   whether the code or the test is wrong, then pushes a fix to your branch (at most 3 automatic commits in a row).
3. When the checks and every review pass, the agent comments `Certified at <sha>` on the pull request.
4. `agent-merge.yml` squash-merges it once the required checks have succeeded on that same commit. A new push
   from you invalidates the certification, and the cycle runs again on the new commit.
5. `changelog.yml` adds the entry to `CHANGELOG.md` after the merge, unless your change already edited it.

If it cannot be made to pass, the pull request gets the label `agent-abandoned` and a comment with the reason;
your branch is left as it is.

## How a change ends

Every change ends in one of three ways, and none waits for a person:

| End | When | What the system does |
|---|---|---|
| **Merged** | Its head commit is certified and the required checks (`checks`, `integration`, `workflows`) succeeded on that same commit | `agent-merge.yml` squash-merges it, using the agent token so the push workflows on `main` run |
| **Abandoned** | It did not converge, even after one retry with twice the budget | The PR (if any) is labelled `agent-abandoned`, and closed if the agent opened it; a person's own PR is left open and unmerged. The base branch is untouched |
| **Reverted** | It merged and the pipeline on `main` then failed | `agent-main-guard.yml` takes `main` back to the last green state (every change since the last green run, in one commit; the pipeline's bookkeeping commits are left alone) and says so, with the failure, on the pull request each change came from (label `agent-reverted`). No issue is opened: reverted is where the change ends, and a new pull request starts a new attempt |

**Certification** is a comment by the agent account carrying
`<!-- agent-certified: <sha> -->` for exactly the head commit. A new push changes
the sha, so an old certification never applies to new code; a comment from anyone
else is ignored. It is issued only when the checks and every review passed.

**The revert is conservative.** It happens only if a failed job is one a code
change causes (`build`, `quality-gate`, `k8s-check`, `docker`); not for scanners
or SBOM. Not if `main` was already red before the commit, not for a commit that
is itself an automatic revert, and not once **3 automatic reverts landed in 24
hours**: that circuit breaker also stops automatic merging until they age out.

**Limits that no code removes.** Changes to `.github/workflows/` are outside the
agent's scope (its token has no `workflow` scope, and GitHub rejects the push), so
a person who edits CI merges their own change; for Renovate's workflow bumps, Renovate merges them and a red one is abandoned. And the guarantee is only as strong
as the checks: a defect none of them sees will merge, and the revert is what limits
the damage. A spending cap belongs on the OpenRouter key itself.

## When a test fails: is the code wrong or the test?

No person is asked. Deterministic evidence comes first: each failing test is
re-run on the current tree (passes on re-run: flaky) and on the base commit
(fails there too: preexisting; absent there: added by this change; passes there:
a regression). Then a **failure adjudicator** classifies each one:

| Verdict | Meaning | What happens |
|---|---|---|
| `code_defect` | The test expresses intended behaviour and the code violates it. The default when unsure | The writer fixes the code; the test is not touched |
| `test_defect` | The test asserts behaviour the change **intentionally** redefines | The test steward updates the test, the code stays |
| `environment` | Flaky, network, ordering | Re-run; nobody is blamed |
| `preexisting` | Already failing on the base commit | The writer fixes it as part of the change, so the checks go green |

**Tests are the specification.** The code is fixed unless the change's own stated
intent (title, description, plan) explicitly redefines what the test checks. A
`test_defect` verdict stands only if the model quotes that intent verbatim, and
the quote is checked in code; without a valid quote the verdict becomes
`code_defect`. Deterministic evidence overrides the model.

The **test steward** may change only test files, and the code refuses any change
that deletes a test file, reduces the number of tests or assertions in a file, or
adds `skip`/`xfail`. It also runs proactively when a change touches application
code: it adds tests for what changed, and new tests are checked against the base
source (a test that passes without the change is reported, because it probably
does not test it).

Failures that are not test failures (lint, collection errors) go straight to the
writer without a verdict.

## What it needs

There is no issue-driven flow: every change starts as a pull request (yours, Renovate's or the canary's).

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
- A reviewer that returns no usable reply ends the attempt as not converged; nothing
  is certified by default.
- Cost per role is recorded in the run artifact (`agent-run-<issue>`) and shown
  in the PR.
- If the stated intent is vague and the test is ambiguous, the model picks a
  side; the "tests win" rule makes that predictable, but it will sometimes fix
  code that was right.
- Evidence by re-running a test only works for tests that can run in the agent's
  job. CI-only tests (the integration suite needs PostgreSQL and Redis) come back
  "unreproducible" and are judged on their log and the stated intent.
- The direct-push mode can only react after the push; it cannot stop it.
  Checks that fail on `main` itself are handled by `agent-main-guard.yml` (re-run once, then revert and redo).
- `reusable_agent-review.yml` (reviewers only, no fixes) exists in `ci-shared`
  but is not wired to a trigger here.
