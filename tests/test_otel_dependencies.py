"""Consistency checks for the pinned OpenTelemetry release train.

OpenTelemetry Python publishes two coupled version streams:

* the API/SDK/exporter stream ``1.X.0``
* the instrumentation/semantic-conventions stream ``0.(X + 21)bN``

Mixing streams (e.g. ``opentelemetry-sdk==1.45.0`` with
``opentelemetry-instrumentation-fastapi==0.66b1``) makes pip fail with a
``ResolutionImpossible`` error, because the SDK pins
``opentelemetry-semantic-conventions`` to its own stream.  These tests keep the
pins aligned so a dependency bump cannot silently reintroduce that state.
"""

from pathlib import Path
import re

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

# Offset between the API/SDK minor version and the instrumentation minor
# version of the matching release (1.45.0 <-> 0.66b0, 1.44.0 <-> 0.65b0, ...).
_INSTRUMENTATION_MINOR_OFFSET = 21


def _pinned_version(distribution: str) -> str:
    """Return the exact version pinned for ``distribution`` in requirements.txt."""
    text = REQUIREMENTS.read_text(encoding="utf-8")
    match = re.search(
        rf"^{re.escape(distribution)}\s*==\s*([^\s;]+)",
        text,
        flags=re.MULTILINE,
    )
    assert match is not None, f"{distribution} is not pinned in requirements.txt"
    return match.group(1)


def test_otel_sdk_and_instrumentation_share_a_release_train():
    sdk_version = _pinned_version("opentelemetry-sdk")
    instrumentation_version = _pinned_version("opentelemetry-instrumentation-fastapi")

    sdk_minor = int(sdk_version.split(".")[1])
    instrumentation_match = re.fullmatch(r"0\.(\d+)b(\d+)", instrumentation_version)
    assert instrumentation_match, (
        "unexpected opentelemetry-instrumentation-fastapi version "
        f"{instrumentation_version!r}"
    )
    instrumentation_minor = int(instrumentation_match.group(1))

    assert instrumentation_minor == sdk_minor + _INSTRUMENTATION_MINOR_OFFSET, (
        "opentelemetry-sdk "
        f"{sdk_version} and opentelemetry-instrumentation-fastapi "
        f"{instrumentation_version} come from different OpenTelemetry release "
        "trains; pip will be unable to resolve the semantic-conventions pin"
    )


def test_otel_api_and_sdk_are_pinned_to_the_same_version():
    assert _pinned_version("opentelemetry-api") == _pinned_version("opentelemetry-sdk")


def test_otel_semantic_conventions_is_not_pinned_directly():
    """It is a transitive dependency: pinning it here would fight the SDK pin."""
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*opentelemetry-semantic-conventions\s*==",
        text,
        flags=re.MULTILINE,
    ), (
        "opentelemetry-semantic-conventions must not be pinned in "
        "requirements.txt; it is pinned transitively by opentelemetry-sdk"
    )
