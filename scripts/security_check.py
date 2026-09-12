"""Fail CI when source control contains common secrets, local paths, or private documents."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEXT_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "Langfuse secret": re.compile(r"\blf_sk_[A-Za-z0-9_-]{16,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Windows user path": re.compile(r"\b[A-Z]:[\\/](?:Users|NEW CHAPTER)[\\/]", re.I),
}
DOCUMENT_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_DOCUMENT_ROOT = Path("datasets/samples")


def repository_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPOSITORY_ROOT,
    )
    return [REPOSITORY_ROOT / item.decode() for item in output.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    for path in repository_files():
        relative = path.relative_to(REPOSITORY_ROOT)
        normalized = relative.as_posix()
        is_private_env = path.name == ".env" or (
            path.name.startswith(".env.") and path.name != ".env.example"
        )
        if is_private_env:
            findings.append(f"tracked environment file: {normalized}")
        is_unapproved_document = (
            path.suffix.casefold() in DOCUMENT_SUFFIXES
            and ALLOWED_DOCUMENT_ROOT not in relative.parents
        )
        if is_unapproved_document:
            findings.append(f"document outside synthetic dataset: {normalized}")
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in TEXT_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{label}: {normalized}")

    if findings:
        print("Security check failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print(f"Security check passed ({len(repository_files())} files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
