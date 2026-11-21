# Build stage: dependencies are installed here (it needs pip and, for some wheels, a toolchain). Only the
# resulting virtualenv is copied to the runtime image. The `FROM python:` line below is the single place
# the Python version is written for CI (.github/actions/setup-python reads it): keep it as the FIRST FROM.
FROM python:3.15.2-slim-trixie AS build

RUN python -m venv /venv
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Network tools for the /api/debug endpoints (ping, traceroute): the runtime image has no apt, so they are
# installed here (same Debian release as the base) and only the binaries plus the shared libraries they
# link to are copied over. Everything ends up under /out, with the same paths as in the runtime image.
FROM python:3.15.2-slim-trixie AS nettools
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends iputils-ping traceroute \
    && mkdir -p /out/usr/bin \
    && cp /usr/bin/ping /usr/bin/traceroute /out/usr/bin/ \
    && for b in /usr/bin/ping /usr/bin/traceroute; do \
         for lib in $(ldd "$b" | awk '$3 ~ /^\// {print $3}'); do \
           d="/out$(readlink -f "$(dirname "$lib")")"; mkdir -p "$d"; cp -L "$lib" "$d/$(basename "$lib")"; \
         done; \
       done

# Runtime: distroless CPython on lg-base (no shell, no apt, no curl), built and rebuilt weekly from
# github.com/lorenzogirardi/ACT-lg-baseimg. Pinned to a dated tag; Renovate proposes the next one (renovate.json).
# Keep the Python version here equal to the build stage above (the venv is tied to the interpreter).
FROM lgirardi/lg-python:3.15.2-20261121

# Same uid/gid as before and as the Helm chart's securityContext (runAsUser 10001).
ARG UID=10001
ARG GID=10001

COPY --from=nettools /out/ /
COPY --from=build /venv/lib/python3.15/site-packages /venv/lib/python3.15/site-packages
COPY --chown=$UID:$GID app/ /app/app/
COPY --chown=$UID:$GID alembic/ /app/alembic/
COPY --chown=$UID:$GID alembic.ini pyproject.toml /app/

# Only the venv's site-packages are copied. The venv's interpreter and console scripts (whose shebangs
# point at the build image, python:3.15.2-slim-trixie) are deliberately left behind: copying the ELF
# `bin/python` into a distroless image is what made the container start as /venv/bin/python and die with
# "SyntaxError: source code cannot contain null bytes". PYTHONPATH therefore points at the directory the
# COPY above created (guaranteed by the build stage's interpreter), not at the runtime image's layout.
ENV PYTHONPATH=/venv/lib/python3.15/site-packages

# Fail the build (not the pod) if the copied packages do not load under this interpreter: a layout or
# ABI mismatch would otherwise surface only as a CrashLoopBackOff. The required set is imported
# unconditionally, the ABI-tagged C extensions when the venv ships them. Exec form, so no shell is
# needed; must stay on ONE line.
RUN ["python3", "-c", "import importlib, importlib.util as u; required = ['uvicorn', 'fastapi', 'pydantic', 'pydantic_core', 'asyncpg', 'greenlet']; [importlib.import_module(m) for m in required]; optional = [m for m in ('uvloop', 'httptools', 'cryptography') if u.find_spec(m)]; [importlib.import_module(m) for m in optional]; print('imported', required + optional)"]

WORKDIR /app
USER $UID:$GID
EXPOSE 8000

# No curl in the image: the check is Python, in exec form (Kubernetes uses its own httpGet probes).
# http.client returns the response (including 5xx) instead of raising, so the status branch is always
# reachable; any connection error exits non-zero on its own. The socket timeout stays below the
# 15s HEALTHCHECK timeout, which also covers the process/startup cost of the readiness probe.
# Must stay on ONE line: with a line continuation Docker treats the JSON as a shell-form command and
# wraps it in `/bin/sh -c`, and the distroless image has no /bin/sh.
HEALTHCHECK --interval=30s --timeout=15s --retries=3 CMD ["python3", "-c", "import http.client,sys; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=8); c.request('GET','/api/mgmt/ready'); sys.exit(0 if c.getresponse().status == 200 else 1)"]

# The base image's ENTRYPOINT is `python3`, so the CMD above holds only its arguments and anything
# passed to `docker run` is appended to that entrypoint too: the working form is
# `docker run <image> -m alembic upgrade head` (or `-c '...'`), never
# `docker run <image> python3 -m alembic upgrade head`, which would execute `python3 python3 -m ...`.
# The console scripts under /venv/bin are never invoked: their shebang points at the build image.
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
