# Runtime base image (distroless)

The application image runs on `lgirardi/lg-python`, a distroless CPython built from
[ACT-lg-baseimg](https://github.com/lorenzogirardi/ACT-lg-baseimg): no shell, no package manager, no `curl`,
non-root. It is rebuilt every Sunday from the current Debian packages, so an OS security fix (glibc, OpenSSL)
reaches this image through a version bump here, with no change to the application.

## How the Dockerfile is built

Two stages. `build` is `python:<version>-slim-trixie`: it creates the virtualenv and installs
`requirements.txt` (it needs pip). The runtime stage is `lgirardi/lg-python:<version>-<YYYYMMDD>` and receives only the venv's
`/venv/lib/python3.15/site-packages`, the application and the Alembic files. The first `FROM python:` line is still the one place the
Python version is read from (`.github/actions/setup-python`), so keep it the first `FROM`.

The runtime does not run the venv's interpreter: `/venv/bin/python` is a symlink into the build image's
Python and does not exist in `lg-python`. Both `CMD` and `HEALTHCHECK` instead start the image's own `python3`
with the venv's `site-packages` on `PYTHONPATH` (`ENV PYTHONPATH=/venv/lib/python3.15/site-packages`); the
venv's `bin/` (interpreter and console scripts) is never executed. A build-time `RUN ["python3", "-c", ...]`
import check fails the build, not the pod, if that path does not resolve.

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

## What the image keeps on purpose

- **`ping`, `traceroute`**: the debug endpoints shell out to them, so the Dockerfile's `nettools` stage installs
  `iputils-ping` and `traceroute` and copies only the two binaries and the shared libraries they link to. They work
  as uid 10001 with all capabilities dropped (ICMP datagram sockets), as in the Helm chart. The endpoints are opt-in
  (`DEBUG_ENDPOINTS_ENABLED`) and off in production.

- **`curl_cffi` (outbound `curl` debug tool)**: the `curl` tool (`/api/debug/curl`, MCP `curl`) presents a real
  browser's TLS ClientHello, HTTP/2 settings and headers, because httpx's `python-httpx` fingerprint is rejected by
  basic bot protection. `curl_cffi` is one abi3 wheel (linux amd64 and arm64, glibc >= 2.17) with libcurl-impersonate
  and BoringSSL statically linked; its only shared dependencies are `libc` and `libpthread`, which `lg-python` has.
  It adds about 40 MB unpacked to the venv (the 41 MB `_wrapper` shared object; the 14 MB wheel is what is
  downloaded; `cffi` and `certifi` are already there through `cryptography` and `httpx`) and no process, so
  there is no headless browser and nothing else to run. The build-time import check in the Dockerfile loads it, so
  a wheel that does not fit the interpreter fails the build, not the pod.

## What the image no longer has

- **`curl` for the container health check**: the Dockerfile's `HEALTHCHECK` uses Python. Kubernetes uses the chart's
  `httpGet` probes, which need nothing in the image.
- **A shell to `exec` into**: `kubectl debug -it <pod> --image=busybox --target=pytbak`.
