#!/usr/bin/env python3
"""
Agent Runbook Registry — Secret & sensitive-information sanitizer.

Scans repo files (or a given path) for credential-like and environment-identifying
strings. Any hit is reported; in --strict mode it exits non-zero (so CI can block
a PR). Never uploads secrets, tokens, cookies, private keys, or identifying
environment info.

Usage:
  python3 sanitize.py [--strict] [path...]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Credential / secret patterns (value-like)
SECRET_PATTERNS = [
    (r"(?i)(cookie|authorization|bearer)\s*[:=]\s*\S{8,}", "auth header/cookie value"),
    (r"(?i)\bapi[_-]?key\b\s*[:=]\s*\S{8,}", "API key"),
    (r"(?i)\btoken\b\s*[:=]\s*\S{8,}", "token"),
    (r"(?i)\bpassword\b\s*[:=]\s*\S{6,}", "password"),
    (r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----", "private key"),
    (r"(?i)\bssh[-_ ]?key\b", "ssh key reference"),
    (r"\bJWT\b", "JWT"),
    (r"(?i)refresh[_-]?token", "refresh token"),
    (r"(?i)session[_-]?(id|key|token)", "session identifier"),
    (r"(?i)\bcookie_quark\b\s*[=:]\s*\S{40,}", "quark cookie value"),
    (r"(?i)([a-z0-9]{20,}\.[a-z0-9]{20,}\.[a-z0-9_-]{20,})", "likely JWT"),
]

# Environment identifiers that must be anonymized
IDENTIFIER_PATTERNS = [
    (r"\b(?:1\d{2}|2\d{2}|3\d{2})\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private IPv4 (10/172/192/2xx)"),
    (r"(?i)\b(?:[a-z0-9-]+\.)?(?:926\.ac\.cn|home\.|vpn\.)\b", "domain"),
    (r"(?i)\bcookiecloud\b\s*\S{16,}", "cookiecloud instance"),
]

REDACT_REPLACEMENT = "<REDACTED>"

EXCLUDE_DIRS = {".git", ".github", "node_modules", "__pycache__", "scripts"}
TEXT_EXTS = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".sh", ".toml"}

# Placeholder values inside angle brackets (e.g. <ADMIN_PASSWORD>) are NOT real secrets
PLACEHOLDER_RE = re.compile(r"<[A-Z0-9_]+>|\b(?:xxx|example|placeholder|your-[a-z-]+)\b", re.IGNORECASE)


def scan_file(path: Path, strict: bool) -> int:
    hits = 0
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return 0
    for line_no, line in enumerate(text.splitlines(), 1):
        # Skip lines that are only placeholder references (documentation of where a secret goes)
        for pattern, label in SECRET_PATTERNS:
            m = re.search(pattern, line)
            if not m:
                continue
            value_part = line[m.start():m.end()]
            # If the matched secret-like value is actually a placeholder, don't flag
            if PLACEHOLDER_RE.search(value_part) and not re.search(r"\b[0-9a-f]{40,}\b", value_part):
                continue
            shown = line.strip()
            if len(shown) > 120:
                shown = shown[:120] + "..."
            print(f"HIT {path}:{line_no} [{label}]: {shown}")
            hits += 1
        # Environment identifiers (private IPs, domains) must be anonymized — no placeholder exemption
        for pattern, label in IDENTIFIER_PATTERNS:
            if re.search(pattern, line):
                shown = line.strip()
                if len(shown) > 120:
                    shown = shown[:120] + "..."
                print(f"HIT {path}:{line_no} [{label}]: {shown}")
                hits += 1
    return hits


def main():
    strict = "--strict" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args if args else ["."]

    files = []
    for t in targets:
        p = Path(t)
        if not p.exists():
            print(f"MISSING: {t}")
            continue
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in TEXT_EXTS and not any(part in EXCLUDE_DIRS for part in f.parts):
                    files.append(f)
        else:
            files.append(p)

    total = 0
    for f in sorted(files):
        total += scan_file(f, strict)

    print(f"\nScanned {len(files)} file(s); {total} potential leak(s).")
    if total and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
