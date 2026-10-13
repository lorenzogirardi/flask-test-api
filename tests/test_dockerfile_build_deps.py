"""Guards the Docker base image and its build prerequisites.

``hiredis`` publishes no cp315 wheel, so on the python:3.15 slim image pip has to
compile it from source and therefore needs a C compiler available *before* the
``pip install`` step.
"""

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_dockerfile_uses_python_315_slim():
    content = DOCKERFILE.read_text()
    assert "FROM python:3.15" in content


def test_dockerfile_installs_c_compiler_before_pip_install():
    content = DOCKERFILE.read_text()
    apt_index = content.index("apt-get install")
    pip_index = content.index("pip install")
    assert apt_index < pip_index, "system packages must be installed before pip"

    install_block = content[apt_index:pip_index]
    assert "gcc" in install_block or "build-essential" in install_block, (
        "hiredis has no cp315 wheel and must be compiled in the image"
    )


def test_dockerfile_installs_libc_headers_before_pip_install():
    content = DOCKERFILE.read_text()
    apt_index = content.index("apt-get install")
    pip_index = content.index("pip install")
    install_block = content[apt_index:pip_index]
    assert "libc6-dev" in install_block or "build-essential" in install_block, (
        "libc6-dev provides assert.h, needed to compile hiredis on python:3.15-slim"
    )
