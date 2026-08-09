#!/usr/bin/env python3
"""
Agent Runbook Registry — Risk scanner.

Scans runbook YAML steps and raw text for dangerous commands and risk indicators,
then assigns an overall risk level (0-3).

Usage:
  python3 risk_scan.py [path...]
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent

LEVEL3_PATTERNS = [
    r"\brm\s+-rf\b", r"\bchmod\s+(?:777|a\+rwx)\b", r"\bchown\b",
    r"curl\s+[^|]*\|\s*(?:sh|bash|zsh)", r"wget\s+[^|]*\|\s*(?:sh|bash|zsh)",
    r"read\s+(?:private key|ssh key|id_rsa)", r"\bsudo\s+(?:rm|chmod|chown)\b",
    r"mkfs\.", r"\bdd\s+of=/dev/", r">\s*/etc/", r"iptables\s+-F",
]
LEVEL2_PATTERNS = [
    r"\bsudo\b", r"/etc/", r"apt(-get)?\s+install", r"yum\s+install", r"dnf\s+install",
    r"systemctl\s+(?:restart|stop|disable)", r"ufw\s+allow", r"iptables",
    r"docker\s+(?:daemon|compose\s+down|rmi)", r"update-alternatives", r"useradd|usermod",
]
LEVEL1_PATTERNS = [
    r"docker\s+(?:run|create|start|restart|compose\s+up)", r"mkdir", r"volume",
    r"POST\s+/\w+", r"PUT\s+/\w+", r"DELETE\s+/\w+", r"create_subscription", r"start\s+",
]
LEVEL0_PATTERNS = [
    r"GET\s+/\w+", r"health", r"status", r"search", r"list",
]


def scan_text(text: str) -> dict:
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for lvl, patterns in ((3, LEVEL3_PATTERNS), (2, LEVEL2_PATTERNS), (1, LEVEL1_PATTERNS), (0, LEVEL0_PATTERNS)):
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                counts[lvl] += 1
    # overall level = highest non-zero
    overall = max((lvl for lvl in (3, 2, 1, 0) if counts[lvl] > 0), default=0)
    return {"overall": overall, "counts": counts}


def scan_file(path: Path):
    text = path.read_text(errors="ignore")
    res = scan_text(text)
    flag = "⚠" if res["overall"] >= 2 else ("✓" if res["overall"] <= 1 else "?")
    print(f"{flag} {path}: risk_level={res['overall']} counts={res['counts']}")
    # Print the specific dangerous lines
    if res["overall"] >= 2:
        for line_no, line in enumerate(text.splitlines(), 1):
            for p in LEVEL2_PATTERNS + LEVEL3_PATTERNS:
                if re.search(p, line, re.IGNORECASE):
                    print(f"    L{line_no}: {line.strip()[:100]}")
                    break
    return res


def main():
    args = sys.argv[1:] or ["."]
    worst = 0
    for a in args:
        p = Path(a)
        if p.is_dir():
            for f in p.rglob("*.yaml"):
                if f.name != "manifest.yaml":
                    worst = max(worst, scan_file(f)["overall"])
        else:
            worst = max(worst, scan_file(p)["overall"])
    print(f"\nHighest risk level across scanned files: {worst}")
    sys.exit(1 if worst >= 3 else 0)


if __name__ == "__main__":
    main()
