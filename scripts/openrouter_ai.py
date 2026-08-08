#!/usr/bin/env python3
"""Call the OpenCode Zen chat-completions API from CI with a minimal, stdlib-only client.

OpenCode Zen (https://opencode.ai/zen) exposes an OpenAI-compatible chat-completions
endpoint. The endpoint and the model are both configurable via the environment, so the
same script can target any OpenAI-compatible gateway (including OpenRouter) by setting
OPENROUTER_ENDPOINT / OPENROUTER_MODEL.

Reads configuration from the environment:

  OPENROUTER_API_KEY   (required) — API key (e.g. OpenCode Zen key, or OpenRouter for OpenRouter). Never echoed anywhere.
  OPENROUTER_MODEL     (optional) — model slug, default: deepseek-v4-flash-free (OpenCode Zen "DeepSeek V4 Flash Free")
  OPENROUTER_ENDPOINT  (optional) — API endpoint, default: https://opencode.ai/zen/v1/chat/completions
  OPENROUTER_SITE_URL  (optional) — sent as the HTTP-Referer header (provider ranking credit)
  OPENROUTER_APP_NAME  (optional) — sent as the X-Title header (provider ranking credit)

Accepts the user prompt from a file (--prompt-file), the system prompt from a file
(--system-file) and prints ONLY the model's reply to stdout. Everything else goes to
stderr. Exits non-zero on any failure with a human-readable message.

Security:
  - The API key is never written to stdout/stderr or echoed.
  - The value of OPENROUTER_API_KEY and other common secret patterns are redacted from
    both stdout and stderr as a defense-in-depth measure.
  - Prompt size is capped (--max-chars); oversized inputs are truncated with a marker.

Example:
  OPENROUTER_API_KEY=sk-or-v1-... python scripts/openrouter_ai.py \
      --system-file prompt-system.md \
      --prompt-file prompt-user.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://opencode.ai/zen/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash-free"
DEFAULT_MAX_CHARS = 120_000
DEFAULT_TIMEOUT = 120

# Common secret patterns redacted defensively from any output (defense-in-depth).
_SECRET_RE = [
    re.compile(r"sk-or-v1-[A-Za-z0-9\-_]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
]


class OpenRouterError(Exception):
    """Raised for any API failure."""


def _read_env_secret(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker = f"\n\n[ai-script: input truncated from {len(text)} to {max_chars} chars]"
    return text[: max_chars - len(marker)] + marker


def _redact(text: str, api_key: str | None) -> str:
    if api_key:
        text = text.replace(api_key, "***REDACTED***")
    for pattern in _SECRET_RE:
        text = pattern.sub("***REDACTED***", text)
    return text


def _http_error_message(exc: urllib.error.HTTPError, api_key: str | None) -> str:
    detail = ""
    try:
        body = json.loads(exc.read().decode("utf-8", errors="replace"))
        if isinstance(body, dict):
            err = body.get("error", {})
            if isinstance(err, dict):
                detail = err.get("message", "") or err.get("type", "")
            else:
                detail = str(err)
    except Exception:
        pass
    detail = _redact(detail, api_key)
    msg = f"OpenRouter HTTP {exc.code}: {detail or exc.reason}".strip()
    return _redact(msg, api_key)


def _request(
    *,
    api_key: str,
    model: str,
    endpoint: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float | None,
    timeout: int,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    site_url = _read_env_secret("OPENROUTER_SITE_URL")
    if site_url:
        headers["HTTP-Referer"] = site_url
    app_name = _read_env_secret("OPENROUTER_APP_NAME")
    if app_name:
        headers["X-Title"] = app_name

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise OpenRouterError(_http_error_message(exc, api_key)) from exc
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        if isinstance(exc.reason, (TimeoutError, OSError)) and "timed out" in reason:
            raise OpenRouterError(f"OpenRouter request timed out after {timeout}s") from exc
        raise OpenRouterError(f"OpenRouter connection error: {_redact(reason, api_key)}") from exc
    except TimeoutError as exc:
        raise OpenRouterError(f"OpenRouter request timed out after {timeout}s") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter returned non-JSON response") from exc

    if isinstance(data, dict) and data.get("error"):
        raise OpenRouterError(_redact(str(data["error"]), api_key))

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("OpenRouter response missing choices[0].message.content") from exc

    if not isinstance(content, str):
        raise OpenRouterError("OpenRouter returned empty response")

    return content


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="openrouter_ai.py",
        description="Call OpenRouter chat completions and print only the model reply.",
    )
    parser.add_argument("--system-file", help="File containing the system prompt (optional)")
    parser.add_argument("--prompt-file", help="File containing the user prompt (default: stdin)")
    parser.add_argument("--model", help="Model slug (env OPENROUTER_MODEL overrides)")
    parser.add_argument("--endpoint", help="API endpoint (env OPENROUTER_ENDPOINT overrides)")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="Max prompt chars")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max output tokens")
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout (s)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    api_key = _read_env_secret("OPENROUTER_API_KEY")
    if not api_key:
        print("error: OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 2

    model = args.model or _read_env_secret("OPENROUTER_MODEL") or DEFAULT_MODEL
    endpoint = args.endpoint or _read_env_secret("OPENROUTER_ENDPOINT") or DEFAULT_ENDPOINT

    system = ""
    if args.system_file:
        try:
            with open(args.system_file, "r", encoding="utf-8") as fh:
                system = fh.read()
        except OSError as exc:
            print(f"error: cannot read system file: {exc}", file=sys.stderr)
            return 3

    try:
        if args.prompt_file:
            with open(args.prompt_file, "r", encoding="utf-8") as fh:
                user = fh.read()
        else:
            user = sys.stdin.read()
    except OSError as exc:
        print(f"error: cannot read prompt: {exc}", file=sys.stderr)
        return 3

    user = _truncate(user, args.max_chars)
    system = _truncate(system, args.max_chars)

    try:
        content = _request(
            api_key=api_key,
            model=model,
            endpoint=endpoint,
            system=system,
            user=user,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.timeout,
        )
    except OpenRouterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(_redact(content, api_key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
