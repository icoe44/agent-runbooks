#!/usr/bin/env python3
"""
Agent Runbook Registry — Repo existence checker.

Verifies that a GitHub repository (and optionally a tag/commit) actually exists,
using the public GitHub API. No token required for public repos (rate-limited).

Usage:
  python3 check_repo.py <owner/repo> [tag|commit]
"""
import json
import sys
import urllib.request

GITHUB_API = "https://api.github.com"


def api_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "agent-runbooks", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read())


def main():
    if len(sys.argv) < 2:
        print("Usage: check_repo.py <owner/repo> [tag|commit]")
        sys.exit(2)

    repo = sys.argv[1].strip().lstrip("https://github.com/").rstrip("/")
    if "/" not in repo:
        print(f"Invalid repo: {repo}")
        sys.exit(2)

    try:
        status, data = api_get(f"{GITHUB_API}/repos/{repo}")
    except Exception as e:
        print(f"ERROR: cannot reach GitHub API for {repo}: {e}")
        sys.exit(1)

    if status != 200:
        print(f"FAIL: repo {repo} not found (HTTP {status})")
        sys.exit(1)

    print(f"OK: repo {repo} exists")
    print(f"  default_branch: {data.get('default_branch')}")
    print(f"  description: {(data.get('description') or '')[:100]}")

    # Optional ref check
    if len(sys.argv) >= 3:
        ref = sys.argv[2]
        try:
            status2, _ = api_get(f"{GITHUB_API}/repos/{repo}/git/refs/tags/{ref}")
            if status2 == 200:
                print(f"OK: tag {ref} exists")
            else:
                # try commit sha
                status3, _ = api_get(f"{GITHUB_API}/repos/{repo}/commits/{ref}")
                if status3 == 200:
                    print(f"OK: commit {ref} exists")
                else:
                    print(f"FAIL: ref {ref} not found as tag or commit")
                    sys.exit(1)
        except Exception as e:
            print(f"ERROR: ref check failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
