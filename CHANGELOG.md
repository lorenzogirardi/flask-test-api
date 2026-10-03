# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries are added automatically on every merge to the default branch.

## [Unreleased]

### Added
- Role-based agent pipeline (`agent-pipeline.yml`): an issue labelled `agent` is planned, implemented, checked, reviewed by two independent reviewers, fixed in a bounded loop, finally reviewed, documented and opened as a PR. It never merges.
- Deterministic changelog workflow (`changelog.yml`): one entry per push to `main`, no model involved.
- Documentation architect (`docs-architect.yml`): a plan-only Diataxis proposal for the documentation; it changes no document.
- `ai-autofix-main`: when `build` or `quality-gate` fails on a push to `main`, an automated fix is proposed as a pull request.

### Changed
- Moved all AI workflows to the `ci-shared` `v2` tag; the model is `deepseek/deepseek-v4.1-flash` (`OPENROUTER_MODEL`).
- The AI review sweep now also repairs red CI on the owner's own PRs, but only merges `renovate[bot]` PRs, and leaves `agent/*` PRs to the agent pipeline.
- `modifygit` no longer sets a `GITHUB_TOKEN` env that had no effect on its push.
