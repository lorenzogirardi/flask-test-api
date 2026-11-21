"""The distroless runtime stage must not launch the build-stage virtualenv interpreter.

`/venv` is created by `python -m venv` in the `python:<version>-slim-trixie` build stage, so
`/venv/bin/python` (and every console script's shebang) points into the build image and does not exist
in `lgirardi/lg-python`. The runtime runs the image's own `python3` with the venv's site-packages on
PYTHONPATH instead; these tests keep that contract from regressing.
"""

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_runtime_never_execs_the_venv_interpreter() -> None:
    text = _text()
    # The build stage keeps using the venv for pip.
    assert "RUN /venv/bin/pip install" in text

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for forbidden in ("/venv/bin/python", "/venv/bin/uvicorn", "/venv/bin/alembic"):
            assert forbidden not in stripped, stripped


def test_runtime_puts_the_venv_site_packages_on_the_path() -> None:
    assert "ENV PYTHONPATH=/venv/lib/python3.15/site-packages" in _text()


def test_runtime_does_not_copy_the_venv_interpreter() -> None:
    # Only the venv's site-packages are copied. /venv/bin holds the build image's ELF interpreter and
    # console scripts pointing at it; shipping them makes the container start as /venv/bin/python and die
    # with "SyntaxError: source code cannot contain null bytes".
    text = _text()
    assert "COPY --from=build /venv /venv" not in text
    assert (
        "COPY --from=build /venv/lib/python3.15/site-packages "
        "/venv/lib/python3.15/site-packages" in text
    )


def test_start_command_and_healthcheck_use_the_image_interpreter() -> None:
    text = _text()
    assert (
        # The base image's ENTRYPOINT is already python3: the CMD holds only its arguments.
        'CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'
        in text
    )
    assert 'CMD ["python3", "-c", "import http.client,sys;' in text


def test_healthcheck_is_single_line_exec_form() -> None:
    # A line continuation after HEALTHCHECK makes Docker treat the JSON as shell form and wrap it in
    # `/bin/sh -c`; the distroless image has no /bin/sh, so the check would never run.
    lines = [line for line in _text().splitlines() if line.startswith("HEALTHCHECK")]
    assert len(lines) == 1, lines
    assert not lines[0].rstrip().endswith("\\"), lines[0]
    assert lines[0].rstrip().endswith("]"), lines[0]
    assert 'CMD ["python3", "-c", "import http.client,sys;' in lines[0]


def test_runtime_checks_the_site_packages_layout_at_build_time() -> None:
    # A venv path whose packages do not import must fail the build, not the running pod. The
    # C-extension packages are the ones a layout, ABI or glibc difference breaks, so the check has to
    # name them, not just the three pure-Python top-level packages.
    prefix = 'RUN ["python3", "-c", "import importlib, importlib.util as u;'
    text = _text()
    assert prefix in text
    line = next(line for line in text.splitlines() if line.startswith(prefix))
    for module in (
        "uvicorn",
        "fastapi",
        "pydantic",
        "pydantic_core",
        "asyncpg",
        "greenlet",
        "uvloop",
        "httptools",
        "cryptography",
    ):
        assert module in line, (module, line)
