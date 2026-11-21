# Runtime base image (distroless)

The application image runs on `lgirardi/lg-python`, a distroless CPython built from
[ACT-lg-baseimg](https://github.com/lorenzogirardi/ACT-lg-baseimg): no shell, no package manager, no `curl`,
non-root. It is rebuilt every Sunday from the current Debian packages, so an OS security fix (glibc, OpenSSL)
reaches this image through a version bump here, with no change to the application.

## How the Dockerfile is built

Two stages. `build` is `python:<version>-slim-trixie`: it creates the virtualenv and installs
`requirements.txt` (it needs pip). The runtime stage is `lgirardi/lg-python:<version>-<YYYYMMDD>` and receives
only `/venv`, the application and the Alembic files. The first `FROM python:` line is still the one place the
Python version is read from (`.github/actions/setup-python`), so keep it the first `FROM`.

| | Before (`python:3.15.2-slim`) | Now (`lg-python`) |
|---|---|---|
| Image size | 356 MB | ~241 MB |
| Vulnerabilities (Trivy, all severities) | 444, 4 CRITICAL | 82, 0 CRITICAL |
| Shell, apt, curl in the image | yes | no |

## How it stays up to date

The `lg-python` tag is pinned to a dated build, never `latest`. Renovate (rule in `renovate.json`) orders the
tags with a regex and opens a pull request when a newer build date exists; the build stage and the runtime move in
the same pull request. It goes through the same agent pipeline as any change: `PR Checks` builds the image and
runs the integration suite against it, and it merges when certified and green.

## What the image no longer has

- **`ping`, `traceroute`**: `/api/debug/network/scan` reports `{"error": "ping not installed"}` /
  `{"error": "traceroute not installed"}` for those two; DNS and the TCP check are Python and keep working.
  The debug endpoints are opt-in (`DEBUG_ENDPOINTS_ENABLED`) and off in production. For a full scan in
  development, run the app locally (`uvicorn`) or from a `python:slim` image with `iputils-ping traceroute`.
- **`curl` for the container health check**: the Dockerfile's `HEALTHCHECK` uses Python. Kubernetes uses the chart's
  `httpGet` probes, which need nothing in the image.
- **A shell to `exec` into**: `kubectl debug -it <pod> --image=busybox --target=pytbak`.
