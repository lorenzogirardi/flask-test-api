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


def test_start_command_and_healthcheck_use_the_image_interpreter() -> None:
    text = _text()
    assert (
        'CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'
        in text
    )
    assert 'CMD ["python3", "-c", "import http.client,sys;' in text
