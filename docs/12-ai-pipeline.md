# AI Pipeline (GitHub Actions + OpenCode Zen)

This repository integrates AI features into its existing GitHub Actions pipeline,
driven by two stdlib-only Python helpers:

- `scripts/openrouter_ai.py` — reusable LLM client (OpenCode Zen, OpenAI-compatible)
- `scripts/ai_sanitize.py` — secret redaction + context bundling
- `tests/test_openrouter_ai.py` — local mock-based tests

Four features are wired in:

| # | Feature | Workflow | Trigger |
|---|---------|----------|---------|
| 1 | AI Code Review on Pull Requests | `.github/workflows/ai-review.yml` | `pull_request` (opened/synchronize/reopened) |
| 2 | AI analysis of lint and test results (two jobs) | `.github/workflows/pipeline.yml` → `ai-analysis-lint`, `ai-analysis-tests` | `push` to `main` (existing pipeline) |
| 3 | Automatic issue triage | `.github/workflows/issue-triage.yml` | `issues` (opened), only `bug`-labeled |
| 4 | Automatic release notes on merge | `.github/workflows/release-notes.yml` | `pull_request` (closed, merged) |

## Architecture

```
GitHub Actions ──► scripts/openrouter_ai.py ──► OpenCode Zen (https://opencode.ai/zen/v1)
                        (stdlib only)                model: deepseek-v4-flash-free
```

- `scripts/openrouter_ai.py` — reusable client: reads key/model/endpoint from the environment,
  accepts a multiline prompt from a file or stdin, validates response JSON, handles HTTP
  errors and timeouts, caps prompt size, and never prints secrets.
- `scripts/ai_sanitize.py` — redacts secrets and caps size of CI output before it is sent to
  the model (bundle mode) and checks a file for secrets before uploading it as an artifact
  (check mode).
- `tests/test_openrouter_ai.py` — local tests that hit a mock OpenAI-compatible HTTP server;
  no real network calls, no API key needed.

## GitHub Configuration

### 1. API key (secret)

Create an OpenCode Zen key at https://opencode.ai/auth, then store it as a **repository secret**:

```bash
gh secret set OPENROUTER_API_KEY --repo lorenzogirardi/flask-test-api --body 'sk-or-...'
```

or via the UI: **Settings → Secrets and variables → Actions → New repository secret**.

> The key is only ever used in the `Authorization: Bearer` header. It is never logged,
> never included in a prompt, and never uploaded as an artifact.

### 2. Model (variable, optional)

Default is already **`deepseek-v4-flash-free`**. To override, set a repository variable:

```bash
gh variable set OPENROUTER_MODEL --repo lorenzogirardi/flask-test-api --body 'deepseek-v4-flash-free'
```

### 3. Referrer / App name (variables, optional)

These are sent as `HTTP-Referer` and `X-Title` headers (ranking credit for the provider):

```bash
gh variable set OPENROUTER_SITE_URL --repo lorenzogirardi/flask-test-api --body 'https://github.com/lorenzogirardi/flask-test-api'
gh variable set OPENROUTER_APP_NAME --repo lorenzogirardi/flask-test-api --body 'GitHub Actions AI'
```

### 4. Enable / disable the AI features

All AI jobs are gated by the repository variable `AI_ENABLED`:

```bash
gh variable set AI_ENABLED --repo lorenzogirardi/flask-test-api --body 'true'   # enable
gh variable set AI_ENABLED --repo lorenzogirardi/flask-test-api --body 'false'  # disable
```

When `AI_ENABLED != 'true'`, every job that talks to the model is skipped and the
pipeline keeps its previous deterministic behavior (build, tests, lint, docker, trivy,
checkov, k8s-check all unchanged).

The endpoint is configurable via the variable `OPENROUTER_ENDPOINT`
(default: `https://opencode.ai/zen/v1/chat/completions`).

### Example configuration (no real values)

```bash
# Secret
OPENROUTER_API_KEY=<GitHub Actions secret>
# Variables
OPENROUTER_MODEL=deepseek-v4-flash-free            # DeepSeek V4 Flash Free on OpenCode Zen
OPENROUTER_ENDPOINT=https://opencode.ai/zen/v1/chat/completions
OPENROUTER_SITE_URL=https://github.com/<owner>/<repo>
OPENROUTER_APP_NAME=GitHub Actions AI
AI_ENABLED=true
```

### 5. Required GitHub permissions

| Workflow | Permissions |
|----------|-------------|
| `ai-review.yml` | `contents: read`, `pull-requests: write` (post/update review comment) |
| `pipeline.yml` (`ai-analysis-lint`, `ai-analysis-tests`) | `contents: read`, `actions: read` (download/upload artifacts) |
| `issue-triage.yml` | `issues: write`, `contents: read` |
| `release-notes.yml` | `contents: read` (artifact upload) |

No workflow requests `write-all` or the `write-all` permission set.

### 6. Local validation of the OpenRouter script

```bash
# Without any real call (mock server) — uses tests only, no network:
pytest tests/test_openrouter_ai.py -v

# Interactive smoke test with a real key (not required for CI):
echo 'Say hi' | OPENROUTER_API_KEY='sk-or...' python3 scripts/openrouter_ai.py
```

### 7. Fork pull requests

Workflows triggered by `pull_request` from forks run with a read-only `GITHUB_TOKEN` and do
not receive repository secrets. On fork PRs the `ai-review.yml` job clears the API key up
front, so the model is not called with repository secrets; the review comment then reports
that AI review did not run. We deliberately do **not** use `pull_request_target`, so
untrusted fork code never gets access to the runner's secrets.

### 8. Informative vs blocking features

- **Deterministic (blocking, unchanged)**: `build` (flake8 + pytest), `docker`
  (build/push), `security-gate-trivy` (scan, report-only), `quality-gate` (checkov),
  `k8s-check`. Failures still fail the pipeline exactly as before.
- **AI (informative)**: `ai-analysis-lint` (flake8-only report), `ai-analysis-tests`
  (pytest-only report), AI code review (comment only), issue triage (labels/comments only),
  release notes (artifact/comment only). They never turn a red pipeline green and never block.

## Security notes

- AI review prompts exclude `.env`, keys/certificates, `.git`, `node_modules`, `vendor`,
  `dist`, `build`, minified maps, and binary assets (see per-path excludes in
  `ai-review.yml`).
- Generated AI reports are scanned for secret patterns by `ai_sanitize.py --check` before
  being uploaded as artifacts.
- Prompt content (issue bodies, PR titles/bodies, diffs) is treated as untrusted data and
  the system prompts instruct the model to ignore embedded instructions. Malicious
  model output is never executed as commands.
- The `.ai/` working directory used by the jobs is gitignored and never committed.
- the code only reads diffs/tests to the model. no GitHub token or repository secret goes
  into a prompt.