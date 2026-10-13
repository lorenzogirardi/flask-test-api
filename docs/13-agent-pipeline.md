# Agent pipeline (ci-shared v3)

Role-based agents that review, repair, certify and merge every pull request, plus a
changelog step and a documentation architect. One graph, opened and closed by an architect: it reads
the code and writes a brief; a developer does the work; a second developer pairs with it; a QA tester,
an SRE, a security role that reports what the tools found and a documentation writer follow; the
architect closes. The roles and the code that acts
on their output live in `ci-shared` (tag `v3`), so other repositories can reuse
them. This repository only wires them up. For the older single-purpose AI
workflows see [12-ai-pipeline.md](12-ai-pipeline.md).

## What runs when

| Change | Workflow | What happens |
|---|---|---|
| Any pull request, Renovate's included since #307 | `agent-change.yml` (job `pull-request`) | The author's title and description are the task. Checks, then the architect's brief; the developer agent does what it asks (commits **pushed to the PR branch**); a second developer accepts or sends back; QA adds the missing tests; SRE and security when the files call for them; the documentation reviewer; the architect closes. One comment on the PR, edited on every run: what happened, the brief, every role's findings and what the tools reported. |
| `PR Checks` fails on a PR (not Renovate's) | `agent-ci-failure.yml` | The failing checks' real logs are the first input, including `integration`. Each failing test gets a verdict (below) before anything changes. Fixes are pushed to the PR branch; it stops after 3 consecutive agent commits that still fail CI. |
| Push straight to `main` with no PR | `agent-change.yml` (job `direct-push`) | Same review. If something blocks it opens a fix PR from `agent/push-<sha>` (never pushes to `main`); otherwise it leaves a commit comment with the advisory findings. |
| Renovate PRs, also | `ai-review-sweep.yml` | A second engine, still the one that repairs and merges them; the graph reviews and merges them too (seen on #313), so such a pull request gets two comments. It goes once the graph has been seen to repair a dependency update with red checks. Starts by itself when a PR's CI ends and when `main` moves; the cron is a safety net. A PR that fell behind `main` (counted from the commits, since this repo has no branch protection) is refreshed: Renovate is asked to rebase its own (label `rebase`), so CI runs on current code, including the `image` check. The sweep then waits for the required checks, gives the reviewers the check results of that commit as evidence, and merges a clean PR. A blocking finding goes to the writer loop and is pushed if it converges; otherwise, or after 3 automatic fixes in a row, the PR is labelled `agent-abandoned` and closed. A PR that touches `.github/workflows/` is reviewed like any other, and the agents repair what is outside the workflow files (no agent edits a workflow file). The verdict is written as the commit status `agent-review`; Renovate, which has the permission, merges it itself once every check is green, that status included. If the required checks are red on current code it is labelled `agent-abandoned` and closed, so no one waits on it. |
| Every push to `main` | `changelog.yml` | One deterministic entry. |

Guards against loops and noise: every commit the pipeline makes has the author
`ci-shared agents`, and a run whose head commit has that author and already carries
a verdict does nothing (one without a verdict is reviewed, at most 3 in a row); a
push whose commit belongs to a PR is skipped, because the PR was reviewed. Only one
agent run works on a pull request at a time: when `PR Checks` fails,
`agent-ci-failure.yml` takes over and the run started by the push is cancelled.
A run that finishes after the branch has moved publishes nothing.
A change the agent did not alter is certified by the first review alone, with
no extra calls. Pushes to a PR branch are made with `AUTOFIX_PUSH_TOKEN`, so the
PR checks re-run on them.

## Reading the Actions tab

Twelve workflows, but only three moments. Runs started by another workflow finishing (`workflow_run`) are
listed under the branch `main` by GitHub even when they are about a pull request; their title says what
they are about (`Agent Merge · workflow_run · <pull request title>`).

| Moment | Workflows, in the order they start |
|---|---|
| A pull request is opened or updated | `PR Checks` (jobs `checks`, `integration`, `image`, `workflows`) and `Agent Change` (reviewers, fixes, certification) start together. When `PR Checks` ends: `Agent CI Failure` (repairs if red), `Agent Merge` (merges if certified and green), `AI Review Sweep` (Renovate pull requests only). After the merge: `AI Release Notes`. |
| Something lands on `main` | `Python application` builds, tests and **publishes the image** (`build`, `docker`, `security-gate-trivy`, `docker-sbom`, `quality-gate`, `modifygit` bumps the tag in `helm/pytbak/values.yaml`, `k8s-check` deploys the published image), next to `Changelog`, `Agent Merge`, `AI Review Sweep` and `Agent Change`. When `Python application` ends red: `Agent Main Guard`. |
| Time passes | `Agent Merge` (every 30 minutes), `AI Review Sweep` (twice a day), `Pipeline Health` (every 30 minutes) and `Pipeline Canary` (nightly) pick up whatever an event missed. GitHub starts scheduled workflows late, sometimes by hours, so nothing depends on the clock alone: the first three also start on events. |

Two different images are built: the `image` job of `PR Checks` builds from the pull request and never publishes it
(it proves the code becomes an image that runs); `docker` on `main` builds the same Dockerfile and publishes it.
A run that is `skipped` is a guard that decided it had nothing to do (for instance `Agent Main Guard` when `main` is
green), not a failure.

A merge must be made with the push token, not the job's `GITHUB_TOKEN`: GitHub starts no workflow for events made with
the latter, so a merge made with it would build no image, run no `k8s-check` and leave the guard blind.

## The pipeline checks itself

`pipeline-health.yml` runs on every push to `main`, when `PR Checks` ends, and on a schedule (every 30 minutes, which
GitHub may delay by hours), with no model. It goes red, and says why in the run summary, when:

- a commit is on `main` and no `Python application` run covers it (it then starts that workflow on `main`). A merge
  made with the job's `GITHUB_TOKEN` causes exactly this, and three dependency bumps once stayed unbuilt for hours;
- a pull request was certified although an agent could not do its job (reported for one day: it can be noticed, not
  repaired after the fact);
- one of the agent workflows is failing: a failed run with no successful run of the same workflow after it;
- a pull request is open with no verdict on its head commit (neither certified nor abandoned) and nothing has run on it
  for 90 minutes. It is then abandoned, so it never waits for a person; a new push starts a new attempt.

## The canary: known changes, checked outcomes

`pipeline-canary.yml` runs once a day (scheduled for the night; GitHub may start it hours later). For the scenario in `.github/canary.json` it opens one pull request that changes
`app/canary.py` (a module nothing imports) in a known way, against a throwaway copy of `main`. The ordinary workflows
run on it; the canary then checks facts and closes it. It is never merged.

| Scenario | The change | What must happen |
|---|---|---|
| `change` | In one pull request: a bug the existing tests catch, described vaguely, and a new function added with no test | The agent restores the code, the test steward adds a test for the new function, which stays as written, nothing outside `app/canary.py` and `tests/` changes, the commit is certified |

It used to be three scenarios in three pull requests, on every run and on every release of `ci-shared`: 36 of them in
one day. A change of behaviour made on purpose, where a test must be updated, is no longer in the canary.

The same scenario also guards the engine itself: before `ci-shared` moves its `v3` tag to a new commit it starts this
canary in candidate mode (`repository_dispatch`), where the pull request is judged by the engine about to be released.
The tag moves only if the scenario holds.

The scenario also states what the agents' report must say (`code_defect`, and no `test_defect`): the
right files reached through the wrong verdict are a failure too.

A red run means the agents did something else: no verdict, an abandonment, a file changed that should not be, a test
weakened. The health check reports a failed canary like any failed agent workflow.

## What to expect on your own pull request

Open a pull request from a branch as usual, with a title that says what it does (the title and description are
the agent's only statement of intent, and the changelog entry is made from the title). Nothing else is needed.

1. `PR Checks` runs the lint and unit tests, the integration suite against real PostgreSQL and Redis, the
   image built from your branch, and the workflow lint.
2. `agent-change.yml` starts the graph. The architect reads the code and writes a brief: what must
   change, what the tests must check, whether infrastructure, security and documents are concerned. The
   developer agent does what the brief asks, also on your pull request; a second developer accepts the
   result or sends it back, three times at most. If the change touches application code, QA adds the
   tests it lacks. The SRE and security look when the files touched call for them, and leave notes. The
   documentation reviewer brings the documents in line, and the architect closes: if its brief asked for
   something nobody did, the developer is asked once more. If a check fails, `agent-ci-failure.yml` reads the failing logs and decides
   whether the code or the test is wrong, then pushes a fix to your branch (at most 3 automatic commits in a row).
3. When the checks pass and the work is closed, the agent comments `Certified at <sha>` on the pull
   request. The comment opens with what happened, in plain words, and the architect's brief; findings,
   what the tools reported and the notes are below it. Nothing in them holds a change that works.
4. `agent-merge.yml` squash-merges it once the required checks have succeeded on that same commit. A new push
   from you invalidates the certification, and the cycle runs again on the new commit.
5. `changelog.yml` adds the entry to `CHANGELOG.md` after the merge, unless your change already edited it.

If it cannot be made to pass, the pull request gets the label `agent-abandoned` and a comment with the reason;
your branch is left as it is.

## How a change ends

Every change ends in one of three ways, and none waits for a person:

| End | When | What the system does |
|---|---|---|
| **Merged** | Its head commit is certified and the required checks (`checks`, `integration`, `image`, `workflows`) succeeded on that same commit | `agent-merge.yml` squash-merges it, using the agent token so the push workflows on `main` run |
| **Abandoned** | Its checks could not be made to pass, twice (the architect starts the work over once), or a role that must answer (the second developer, the documentation reviewer) gave no usable answer. A test QA could not write does not end a change: it is said in the comment | The PR (if any) is labelled `agent-abandoned`, and closed if the agent opened it; a person's own PR is left open and unmerged. The base branch is untouched |
| **Reverted** | It merged and the pipeline on `main` then failed | `agent-main-guard.yml` takes `main` back to the last green state (every change since the last green run, in one commit; the pipeline's bookkeeping commits are left alone) and says so, with the failure, on the pull request each change came from (label `agent-reverted`). No issue is opened: reverted is where the change ends, and a new pull request starts a new attempt |

**Certification** is a comment by the agent account carrying
`<!-- agent-certified: <sha> -->` for exactly the head commit. A new push changes
the sha, so an old certification never applies to new code; a comment from anyone
else is ignored. It is issued only when the checks passed and the second developer answered.

**The revert is conservative.** It happens only if a failed job is one a code
change causes (`build`, `quality-gate`, `k8s-check`, `docker`); not for scanners
or SBOM. Not if `main` was already red before the commit, not for a commit that
is itself an automatic revert, and not once **3 automatic reverts landed in 24
hours**: that circuit breaker also stops automatic merging until they age out.

**Limits that no code removes.** No agent edits a file under `.github/workflows/`: a change to the
pipeline is written by a person. It is reviewed and merged like any other (the agents' token has the
`workflow` permission since 2026-10-11; seen on #306, #307 and #308). For Renovate's workflow bumps, the
agents review them, Renovate merges them and a red one is abandoned. And the guarantee is only as strong
as the checks: a defect none of them sees will merge, and the revert is what limits
the damage. A spending cap belongs on the OpenRouter key itself; when it is reached every pull request
ends abandoned (the comment names the role that had no answer, the cause is in the job log), and a commit
abandoned that way is reviewed again only after a new push.

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
intent (title, description) explicitly redefines what the test checks. A
`test_defect` verdict stands only if the model quotes that intent, and the quote is
checked in code: every piece of it (pieces may be joined by `...`) must be in the
intent word for word. Without a valid quote the verdict becomes `code_defect`.
Deterministic evidence overrides the model, and it counts only when pytest really
ran the test: a job that cannot run it gives "unreproducible", never "failing".

Three consequences, all enforced in code:

- After a `code_defect` verdict the writer may not edit the file of the failing
  test. A change that does is reverted and refused; a second one ends without
  certification.
- A test the steward has just written or rewritten is not the specification. If it
  fails it is discarded and the steward is asked again with the failure; the
  application is never changed to satisfy it.
- An agent that must answer and cannot (the steward, the documentation reviewer) is
  told what was wrong and tries once more. If that fails too the commit is not
  certified. The same holds without an answer from the second developer. A role that
  only informs (security, SRE, architect) and gives no answer is reported in the
  comment, and the change goes on.

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
`AUTOFIX_PUSH_TOKEN` with **Contents**, **Pull requests** and **Workflows** read/write on
this repository (the last one lets the merge gate merge a change to a workflow file). The token pushes and merges, so that the checks and the
pipeline on `main` start; a push or a merge made with the job's `GITHUB_TOKEN`
starts nothing. Pull requests the pipeline opens itself (the canary's, a fix after
a direct push) are opened with the job token, which needs the repository setting
*Allow GitHub Actions to create and approve pull requests*, and are then started
by a push made with the push token.

## What happens

The title and description of the pull request are the task. The architect turns them, with the code,
into the brief every other role works from.

| Step | Role | Notes |
|---|---|---|
| 1 | Deterministic checks | Same steps as `pr-checks.yml` (dependency resolution, install, lint, tests, smoke test). Run first, and after every change. |
| 2 | Architect: the brief | Reads the code and what the checks said. It has tools to look things up, and chooses among them: read and search the code, `docs` (what a library says changed, from the pages the library names for itself), `usages`, `imports`, `signature`, `history`, `tests`, `api`, `evidence` (Trivy, Checkov, SBOM, deploy), `runs`. All read-only. |
| 3 | Developer | Does what the brief asks: at most 8 changes per turn, unique-anchor edits or new files, never `.github/workflows/`. A change that fails the checks is reverted and fed back. When the brief finds the change right as submitted, nothing is written. |
| 4 | Second developer (the pair) | Reads the result with the brief and the whole files. Accepts, or sends back: a `critical` or `high` finding, and the first time also a `medium` one that is a defect. Three times at most; then the architect decides. |
| 5 | QA | When application code changed: adds the tests the brief calls for. They are run by step 1. Tests of its own that do not pass, twice, are taken out and the change goes on. |
| 6 | SRE and security, side by side | Only when the files touched or the brief call for them. They read what the tools reported for the commit and for the base, and inform. |
| 7 | Documentation reviewer | Gets the passages of the documents that mention what the diff touches. Edits only documentation files (never `CLAUDE.md`, `AGENTS.md` or `.claude/`), then re-runs the checks. |
| 8 | Architect: the close | Says what happened. What its brief asked for and nobody did goes back to the developer once. |
| 9 | Changelog | A deterministic entry in `CHANGELOG.md` unless the change already has one. |

All agents use the model in `OPENROUTER_MODEL`. The roles that write code or the brief think before
they answer (developer, QA, architect); the others answer at once, in seconds. The record of a run
(what each role did and found) is in the job's artifact, under `agents-run/`.

Seen here: the release canary of the engine (#314), where the architect's brief named the planted
defect, the developer repaired it and QA added the tests, certified in about two minutes. Not yet seen
here: a dependency update with red checks, the SRE and security side by side, the close sending work back.

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

- The loop is bounded: three rounds of the pair, `max_verify_retries` failed-check retries,
  `writer_rounds` turns of the developer, one second cycle from the architect.
- The architect is one point of failure: a wrong brief is followed by everyone. The checks, the roles
  the touched files oblige and the brief published in the comment are what limit it.
- Without a usable reply from the second developer nothing is certified.
- The second developer answers with no thinking: it sees an evident defect and weighs a
  subtle one less well. What is left unresolved is merged with the finding written in the comment.
- Cost per role is recorded in the run artifact (`agent-change-pr-<run>`) and shown
  in the PR.
- If the stated intent is vague and the test is ambiguous, the model picks a
  side; the "tests win" rule makes that predictable, but it will sometimes fix
  code that was right.
- Evidence by re-running a test only works for tests that can run in the agent's
  job. CI-only tests (the integration suite needs PostgreSQL and Redis) come back
  "unreproducible" and are judged on their log and the stated intent.
- The direct-push mode can only react after the push; it cannot stop it.
  Checks that fail on `main` itself are handled by `agent-main-guard.yml` (re-run once, then revert).
- A description is part of the input. One that promises behaviour the code does
  not have sends the agents looking for it; the rules above keep the outcome
  safe, but the change may be abandoned instead of merged.
- The canary covers one scenario (a bug to repair and a function to test). A defect it
  does not exercise is not seen before a release of the engine; a change of behaviour made
  on purpose is no longer in it.
- `reusable_agent-review.yml` (reviewers only, no fixes) and
  `reusable_agent-pipeline.yml` (planner, from a written request) exist in
  `ci-shared` but are not wired to a trigger here.
