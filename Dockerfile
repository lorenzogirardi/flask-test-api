# Build stage: dependencies are installed here (it needs pip and, for some wheels, a toolchain). Only the
# resulting virtualenv is copied to the runtime image. The `FROM python:` line below is the single place
# the Python version is written for CI (.github/actions/setup-python reads it): keep it as the FIRST FROM.
FROM python:3.15.2-slim-trixie AS build

RUN python -m venv /venv
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Runtime: distroless CPython on lg-base (no shell, no apt, no curl), built and rebuilt weekly from
# github.com/lorenzogirardi/ACT-lg-baseimg. Pinned to a dated tag; Renovate proposes the next one (renovate.json).
# Keep the Python version here equal to the build stage above (the venv is tied to the interpreter).
FROM lgirardi/lg-python:3.15.2-20261121

# Same uid/gid as before and as the Helm chart's securityContext (runAsUser 10001).
ARG UID=10001
ARG GID=10001

COPY --from=build /venv /venv
COPY --chown=$UID:$GID app/ /app/app/
COPY --chown=$UID:$GID alembic/ /app/alembic/
COPY --chown=$UID:$GID alembic.ini pyproject.toml /app/

WORKDIR /app
USER $UID:$GID
EXPOSE 8000

# No curl in the image: the check is Python, in exec form (Kubernetes uses its own httpGet probes).
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["/venv/bin/python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/mgmt/ready', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["/venv/bin/python", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
