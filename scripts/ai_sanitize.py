#!/usr/bin/env python3
"""Sanitize and cap the size of CI test/lint output before sending it to an LLM.

Used in .github/workflows/pipeline.yml (ai-analysis) to build a safe
.ai/security-context.txt and to guard uploaded artifacts: the AI must never
receive or re-publish secrets.

Two modes:

  bundle  (default)
      python3 scripts/ai_sanitize.py --out FILE --max-bytes N FILE...
      Rewrites each input file's content redacting secret patterns, prepends a
      small header block per file, and truncates the result to at most N bytes.
      Exits 0 if at least one byte was written, 1 otherwise.

  check:
      python3 scripts/ai_sanitize.py --check FILE
      Exits 0 if FILE contains no detectable secret patterns, 1 if it does.
      Used before uploading an artifact to avoid publishing secrets.

Stdlib only; safe to run in any Ubuntu runner.
"""

from __future__ import annotations

import argparse
import re
import sys

_SECRET_RE = [
    re.compile(r"sk-or-v1-[A-Za-z0-9\-_]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)(DATABASE_URL|REDIS_URL|WEBHOOK_URL|MONGO_URL|MYSQL_URL|AMQP_URL|PASSWORD)\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),  # JWT
]


def redact(text: str) -> str:
    for pattern in _SECRET_RE:
        text = pattern.sub("***REDACTED***", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check a sanitized AI context file.")
    parser.add_argument("--check", action="store_true", help="Check a file for secrets instead of building")
    parser.add_argument("--out", help="Output file for --build mode")
    parser.add_argument("--max-bytes", type=int, default=150_000, help="Max output size in bytes")
    parser.add_argument("files", nargs="+", help="Input files (or one file in --check mode)")
    args = parser.parse_args()

    if args.check:
        path = args.files[0]
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        return 1 if redact(content) != content else 0

    parts: list[str] = []
    total = 0
    for path in args.files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue
        safe = redact(content)
        block = f"### {path} ({len(content)} chars)\n{safe}\n"
        parts.append(block)
        total += len(block)
        if total >= args.max_bytes:
            break

    if not parts:
        print("error: no input files produced content", file=sys.stderr)
        return 1

    out = "\n".join(parts)[: args.max_bytes]
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())