#!/usr/bin/env python3
"""
Agent Runbook Registry — Registry index generator.

Scans runbooks/ and attestations/ and emits registry/index.json.
Run by CI; never hand-edit index.json.

Usage:
  python3 build_registry.py [--out registry/index.json]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def runbook_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def parse_repo_path(p: Path) -> str:
    """runbooks/github.com/<owner>/<repo>/... -> owner/repo"""
    parts = p.relative_to(ROOT).parts
    try:
        gi = parts.index("github.com")
        return f"{parts[gi+1]}/{parts[gi+2]}"
    except (ValueError, IndexError):
        return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "registry" / "index.json"))
    args = parser.parse_args()

    index = {}

    runbooks_root = ROOT / "runbooks" / "github.com"
    if runbooks_root.exists():
        for rb in runbooks_root.rglob("*.yaml"):
            if rb.name == "manifest.yaml":
                continue
            repo = parse_repo_path(rb)
            # goal = filename stem
            goal = rb.stem
            ref = rb.parent.name  # versions/<ref>
            entry = index.setdefault(repo, {"latest_known_upstream": None, "runbooks": {}})
            entry["runbooks"][f"{goal}@{ref}"] = {
                "status": "community",
                "hash": runbook_hash(rb),
                "path": str(rb.relative_to(ROOT)),
            }

    # Merge attestations counts
    attest_root = ROOT / "attestations" / "github.com"
    if attest_root.exists():
        for att in attest_root.rglob("attestation-*.json"):
            repo = parse_repo_path(att)
            if repo not in index:
                index[repo] = {"latest_known_upstream": None, "runbooks": {}}
            try:
                a = json.loads(att.read_text())
                rh = a.get("runbook_hash", "")
                result = a.get("result", "unknown")
                # find runbook by hash
                for goal_key, meta in index[repo]["runbooks"].items():
                    if meta.get("hash") == rh:
                        meta["attestations"] = meta.get("attestations", 0) + 1
                        if result == "success":
                            meta["success_attestations"] = meta.get("success_attestations", 0) + 1
            except Exception:
                pass

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    print(f"Registry written: {out}")
    print(f"Repos: {len(index)}")


if __name__ == "__main__":
    main()
