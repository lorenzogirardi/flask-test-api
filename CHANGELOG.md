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
- A CI job that fails in the runner rather than in the code (runner start-up, checkout, cluster creation) is re-run once instead of being sent to the repair loop; the independent reviewers now run at the same time, and a review finding about a file the plan declared out of scope is not acted on.
- Lower the Fibonacci input limit from 20000 to 10000 ([#190](https://github.com/lorenzogirardi/flask-test-api/pull/190))
- Lower the Fibonacci input limit from 10000 to 5000 ([#193](https://github.com/lorenzogirardi/flask-test-api/pull/193))
- Lower the sleep limit from 30 to 25 seconds ([#197](https://github.com/lorenzogirardi/flask-test-api/pull/197))
- The readiness probe says which version is serving ([#302](https://github.com/lorenzogirardi/flask-test-api/pull/302))

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
- Update actions/setup-python action to v7 ([#164](https://github.com/lorenzogirardi/flask-test-api/pull/164))
- Warm the Redis connection before counting ([#171](https://github.com/lorenzogirardi/flask-test-api/pull/171))
- Leave workflow PRs to Renovate, abandon red ones ([#172](https://github.com/lorenzogirardi/flask-test-api/pull/172))
- Update bridgecrewio/checkov-action action to v12.3129.0 ([#173](https://github.com/lorenzogirardi/flask-test-api/pull/173))
- Update step-security/harden-runner action to v2.22.0 ([#174](https://github.com/lorenzogirardi/flask-test-api/pull/174))
- Update helm/kind-action action to v1.15.1 ([#175](https://github.com/lorenzogirardi/flask-test-api/pull/175))
- Update bridgecrewio/checkov-action action to v12.3130.0 ([#176](https://github.com/lorenzogirardi/flask-test-api/pull/176))
- Update bridgecrewio/checkov-action action to v12.3131.0 ([#181](https://github.com/lorenzogirardi/flask-test-api/pull/181))
- Update step-security/harden-runner action to v2.22.1 ([#184](https://github.com/lorenzogirardi/flask-test-api/pull/184))
- Say what each workflow_run run is about; map the workflows in the docs ([#187](https://github.com/lorenzogirardi/flask-test-api/pull/187))
- Keep the commit message out of run names ([#189](https://github.com/lorenzogirardi/flask-test-api/pull/189))
- Pipeline health check; one agent at a time on a pull request ([#196](https://github.com/lorenzogirardi/flask-test-api/pull/196))
- Let the health check abandon a pull request that has no verdict ([#198](https://github.com/lorenzogirardi/flask-test-api/pull/198))
- Nightly pipeline canary on an isolated module ([#199](https://github.com/lorenzogirardi/flask-test-api/pull/199))
- Let the canary open and close its pull requests ([#200](https://github.com/lorenzogirardi/flask-test-api/pull/200))
- Remove the issue-driven flows; a revert is reported on the pull request ([#203](https://github.com/lorenzogirardi/flask-test-api/pull/203))
- Simplify the comparison in the canary helper ([`6605ad6`](https://github.com/lorenzogirardi/flask-test-api/commit/6605ad6))
- Refactor: simplify the comparison in the canary helper (pipeline red) ([`f0abce4`](https://github.com/lorenzogirardi/flask-test-api/commit/f0abce4))
- Describe the agent pipeline and the canary module in CLAUDE.md ([#210](https://github.com/lorenzogirardi/flask-test-api/pull/210))
- A scenario for new code that has no test ([#211](https://github.com/lorenzogirardi/flask-test-api/pull/211))
- The canary can judge a candidate engine before ci-shared releases it ([#215](https://github.com/lorenzogirardi/flask-test-api/pull/215))
- The scenarios also check the verdict the agents gave ([#222](https://github.com/lorenzogirardi/flask-test-api/pull/222))
- Make the pipeline documents say what the pipeline does ([#231](https://github.com/lorenzogirardi/flask-test-api/pull/231))
- Start the health check on events too, not only on the clock ([#244](https://github.com/lorenzogirardi/flask-test-api/pull/244))
- Update dependency python to 3.15 ([#245](https://github.com/lorenzogirardi/flask-test-api/pull/245))
- Let the sweep write its review verdict as a commit status ([#246](https://github.com/lorenzogirardi/flask-test-api/pull/246))
- Update bridgecrewio/checkov-action action to v12.3132.0 ([#247](https://github.com/lorenzogirardi/flask-test-api/pull/247))
- Read the Python version from the Dockerfile, the only place it is written ([#257](https://github.com/lorenzogirardi/flask-test-api/pull/257))
- Show Trivy and Checkov findings on the run, without blocking it ([#258](https://github.com/lorenzogirardi/flask-test-api/pull/258))
- Run the awareness tools on pull requests and add TruffleHog ([#262](https://github.com/lorenzogirardi/flask-test-api/pull/262))
- The image job does not rebuild what the parent commit already proved ([#293](https://github.com/lorenzogirardi/flask-test-api/pull/293))
- Update dependency pydantic to v2.14.1 ([#294](https://github.com/lorenzogirardi/flask-test-api/pull/294))
- One pull request per run instead of three ([#303](https://github.com/lorenzogirardi/flask-test-api/pull/303))
- No model call outside the graph on main ([#306](https://github.com/lorenzogirardi/flask-test-api/pull/306))
- The graph reviews the dependency bot's pull requests too ([#307](https://github.com/lorenzogirardi/flask-test-api/pull/307))
- The SBOM of the pull request's image is evidence for the roles ([#308](https://github.com/lorenzogirardi/flask-test-api/pull/308))
- The documents say what the pipeline does now ([#310](https://github.com/lorenzogirardi/flask-test-api/pull/310))
- Update bridgecrewio/checkov-action action to v12.3133.0 ([#313](https://github.com/lorenzogirardi/flask-test-api/pull/313))
- Update lorenzogirardi/ci-shared action to v3 ([#317](https://github.com/lorenzogirardi/flask-test-api/pull/317))
- Call the engine at v3, and describe the graph that starts from the architect ([#318](https://github.com/lorenzogirardi/flask-test-api/pull/318))
- Update python docker tag to v3.15.0 ([#316](https://github.com/lorenzogirardi/flask-test-api/pull/316))
- One engine, and Renovate may propose Python 3.15 again ([#326](https://github.com/lorenzogirardi/flask-test-api/pull/326))
- Update python docker tag to v3.15.0 ([#327](https://github.com/lorenzogirardi/flask-test-api/pull/327))
- Update bridgecrewio/checkov-action action to v12.3134.0 ([#331](https://github.com/lorenzogirardi/flask-test-api/pull/331))
- Update dependency fastapi to v0.143.1 ([#333](https://github.com/lorenzogirardi/flask-test-api/pull/333))
- Update dependency pydantic-settings to v2.16.0 ([#334](https://github.com/lorenzogirardi/flask-test-api/pull/334))
- Update dependency fastapi to v0.143.2 ([#336](https://github.com/lorenzogirardi/flask-test-api/pull/336))
- Update dependency ddtrace to v4.16.0 ([#337](https://github.com/lorenzogirardi/flask-test-api/pull/337))
- Update dependency fastapi to v0.143.3 ([#338](https://github.com/lorenzogirardi/flask-test-api/pull/338))
- Update dependency sqlalchemy to v2.1.5 ([#339](https://github.com/lorenzogirardi/flask-test-api/pull/339))
- Update dependency fastapi to v0.143.5 ([#340](https://github.com/lorenzogirardi/flask-test-api/pull/340))
- Update dependency fastapi to v0.144.0 ([#341](https://github.com/lorenzogirardi/flask-test-api/pull/341))
- Update dependency fastapi to v0.146.0 ([#342](https://github.com/lorenzogirardi/flask-test-api/pull/342))
- Update dependency fastapi to v0.148.0 ([#343](https://github.com/lorenzogirardi/flask-test-api/pull/343))
- Update step-security/harden-runner action to v2.22.2 ([#345](https://github.com/lorenzogirardi/flask-test-api/pull/345))
- Update dependency pydantic-settings to v2.16.1 ([#344](https://github.com/lorenzogirardi/flask-test-api/pull/344))
- Update bridgecrewio/checkov-action action to v12.3135.0 ([#347](https://github.com/lorenzogirardi/flask-test-api/pull/347))
- Update trufflesecurity/trufflehog action to v3.99.3 ([#346](https://github.com/lorenzogirardi/flask-test-api/pull/346))
- Update dependency fastapi to v0.156.4 ([#348](https://github.com/lorenzogirardi/flask-test-api/pull/348))
- Update dependency fastapi to v0.156.7 ([#349](https://github.com/lorenzogirardi/flask-test-api/pull/349))

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
- Sleep endpoint rejects values that are too long ([#191](https://github.com/lorenzogirardi/flask-test-api/pull/191))
- Restore the documented error envelope for 400 responses ([#194](https://github.com/lorenzogirardi/flask-test-api/pull/194))
- The image goes back to Python 3.14 until the agents' engine runs on 3.15 ([#319](https://github.com/lorenzogirardi/flask-test-api/pull/319))
