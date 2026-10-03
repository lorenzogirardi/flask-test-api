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

### Changed
- Moved all AI workflows to the `ci-shared` `v2` tag; the model is `deepseek/deepseek-v4.1-flash` (`OPENROUTER_MODEL`).
- The AI review sweep is limited to Renovate PRs again; all other PRs go through `agent-change.yml`.
- Removed `ai-review.yml`: its single-reviewer comment is replaced by the two independent reviewers of `agent-change.yml`.
- `modifygit` no longer sets a `GITHUB_TOKEN` env that had no effect on its push.
- The integration suite (`tests/integration`) now runs in `PR Checks` (job `integration`, PostgreSQL and Redis as services) and in `k8s-check` against the deployed image in kind with real PostgreSQL and Redis. It was skipped on every CI run and had rotted (14 failures, 18 errors); its HTTP tests are now synchronous.

### Fixed
- `/api/mgmt/mappings` reported included routers as the repr of an internal FastAPI object (`_IncludedRouter(...)`, 63 KB) instead of their routes; the unit test only checked that the key existed.
