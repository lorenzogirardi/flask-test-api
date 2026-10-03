# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries are added automatically on every merge to the default branch.

## [Unreleased]

### Added
- Role-based agent pipeline (`agent-pipeline.yml`): an issue labelled `agent` is planned, implemented, checked, reviewed by two independent reviewers, fixed in a bounded loop, finally reviewed, documented and opened as a PR. It never merges.
- `agent-change.yml`: the same review and fix loop on every pull request except Renovate's (fix commits are pushed to the PR branch) and on every push straight to `main` (a fix PR is opened if something blocks).
- Deterministic changelog workflow (`changelog.yml`): one entry per push to `main`, no model involved.
- Documentation architect (`docs-architect.yml`): a plan-only Diataxis proposal for the documentation; it changes no document.
- `ai-autofix-main`: when `build` or `quality-gate` fails on a push to `main`, an automated fix is proposed as a pull request.
- `tests/k8s/stack.yaml`: the throwaway app + PostgreSQL + Redis stack used by `k8s-check`.
- `agent-ci-failure.yml`: when `PR Checks` fails on a pull request, the agent reads the failing checks' logs, decides for each failing test whether the code or the test is wrong (tests are the specification; a test changes only if the PR's stated intent explicitly redefines it), and pushes the fix to the PR branch, up to 3 consecutive attempts.
- A test steward role that adds tests for changed application code and updates tests the adjudicator found wrong; it cannot delete tests, reduce assertions or add skip/xfail.
- Merge authority: `agent-merge.yml` merges a pull request whose head commit is certified by the agent pipeline and whose required checks (`checks`, `integration`, `workflows`) succeeded on that commit. Certification is bound to the commit sha and trusted only from the agent account.
- `agent-main-guard.yml`: when the pipeline on `main` fails after a merge, the culprit is reverted automatically and an issue labelled `agent` is opened so the change is redone. A circuit breaker (3 automatic reverts in 24h) also stops automatic merging.
- Ai-autofix-main on main failures, limited to code-level gates ([`69a5677`](https://github.com/lorenzogirardi/flask-test-api/commit/69a5677))
- Renovate PRs reviewed by the two independent reviewers ([`6f9670e`](https://github.com/lorenzogirardi/flask-test-api/commit/6f9670e))
- `image` check in PR Checks: the image is built from the pull request, deployed in kind with real PostgreSQL and Redis, and the integration suite runs against it. A Dockerfile or dependency change is now proven before the merge. `image` is required for every merge.
- Allow sleeping up to 30 seconds ([#169](https://github.com/lorenzogirardi/flask-test-api/pull/169))

### Changed
- Moved all AI workflows to the `ci-shared` `v2` tag; the model is `deepseek/deepseek-v4.1-flash` (`OPENROUTER_MODEL`).
- The AI review sweep is limited to Renovate PRs again; all other PRs go through `agent-change.yml`.
- Removed `ai-review.yml`: its single-reviewer comment is replaced by the two independent reviewers of `agent-change.yml`.
- `modifygit` no longer sets a `GITHUB_TOKEN` env that had no effect on its push.
- The integration suite (`tests/integration`) now runs in `PR Checks` (job `integration`, PostgreSQL and Redis as services) and in `k8s-check` against the deployed image in kind with real PostgreSQL and Redis. It was skipped on every CI run and had rotted (14 failures, 18 errors); its HTTP tests are now synchronous.
- A change that does not converge is retried once with twice the budget and then abandoned (labelled, commented, the agent's own PR closed); no outcome waits for a person.
- Fix(ci): grant actions: read to agent-change.yml (pipeline red) ([`ecbedbd`](https://github.com/lorenzogirardi/flask-test-api/commit/ecbedbd))
- Revert "revert(agent): fix(ci): grant actions: read to agent-change.yml (pipeline red)" ([`8185500`](https://github.com/lorenzogirardi/flask-test-api/commit/8185500))
- The Renovate sweep starts by itself when a PR's CI ends and when `main` moves, brings PRs that fell behind up to date, and abandons a PR after 3 automatic fixes in a row that still leave CI red; the twice-daily cron remains as a safety net.
- Renovate review: the reviewers receive the deterministic check results of the exact commit, the sweep waits for required checks instead of judging early, and a blocking finding is fixed by the writer loop or the PR is abandoned (never left waiting). A runtime (Python) bump is judged by the image check, not rejected on principle.
- Update helm/kind-action action to v1.15.0 ([#166](https://github.com/lorenzogirardi/flask-test-api/pull/166))
- What to expect on your own pull request ([#167](https://github.com/lorenzogirardi/flask-test-api/pull/167))
- The sweep's repair of a red Renovate PR now runs on the same engine as every other change (writer, secret-free checks, failure adjudication, two reviewers) instead of a separate loop; the push token is hidden from `.git/config` while the PR's code runs.
- Simplify the fibonacci loop ([#168](https://github.com/lorenzogirardi/flask-test-api/pull/168))

### Removed
- `ai-autofix-main` (a PR to repair a red `main`): `agent-main-guard.yml` already takes `main` back to the last green state and the change is redone by the agent pipeline, so two systems no longer react to the same failure.

### Fixed
- `/api/mgmt/mappings` reported included routers as the repr of an internal FastAPI object (`_IncludedRouter(...)`, 63 KB) instead of their routes; the unit test only checked that the key existed.
- MCP integration tests broke with `mcp` 2.3.0 (it dropped the `auth=` keyword of the streamable-HTTP client, now yields two streams instead of three, and renamed `isError` to `is_error`); the two "is rejected" tests had been passing for the wrong reason (any exception) and now assert a real 401. Found by running the integration suite, which CI had been skipping.
- Grant actions: read to agent-change.yml ([`8560638`](https://github.com/lorenzogirardi/flask-test-api/commit/8560638))
- Start the app only after PostgreSQL and Redis are ready; run the agent on issues opened with the label ([`1dfd80f`](https://github.com/lorenzogirardi/flask-test-api/commit/1dfd80f))
- The main guard re-runs the failed jobs once before reverting anything, after a flaky `k8s-check` made it revert a harmless fix on the first push. Issues created already labelled `agent` (the guard's redo issues) now start the agent pipeline.
- Unused loop variable in the integration job failed the actionlint check ([`614a223`](https://github.com/lorenzogirardi/flask-test-api/commit/614a223))
- `k8s-check` waited for the OLD app pod (`wait --for=condition=available` is already true for it) and could run the tests against an app that had started before PostgreSQL; it now waits for the new pod with `rollout status`.
- A PR that fell behind `main` was never detected (GitHub only reports "behind" with branch protection), so it kept check results from before the base moved and lacked newer checks such as `image`. Staleness is now counted from the commits; Renovate is asked to rebase its own PRs.
- A certified pull request with green CI could stay open: the merge gate trusted only the repository owner while the agent workflows post as `github-actions[bot]`, and when CI ended before the certification no later event picked it up. Both are trusted now, and `agent-merge.yml` judges every open PR on each CI end, on each push to `main` and every 30 minutes.
