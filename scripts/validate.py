#!/usr/bin/env python3
"""
Agent Runbook Registry — Schema & structure validator.

Usage:
  python3 validate.py [path]
    - path: a manifest.yaml, runbook .yaml, or attestation .json file, OR
            a directory (validates all supported files under it).
    - no path: validates the whole repo tree.

Exits non-zero on any validation error.
"""
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate as jsonschema_validate
except ImportError:
    print("ERROR: 'jsonschema' not installed. Run: pip install jsonschema")
    sys.exit(2)

try:
    import yaml
except ImportError:
    print("ERROR: 'pyyaml' not installed. Run: pip install pyyaml")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = {
    "manifest": json.loads((ROOT / "schemas" / "manifest.schema.json").read_text()),
    "runbook": json.loads((ROOT / "schemas" / "runbook.schema.json").read_text()),
    "attestation": json.loads((ROOT / "schemas" / "attestation.schema.json").read_text()),
}

FAILURES = []
WARNINGS = []


def load_doc(path: Path):
    if path.suffix in (".yaml", ".yml"):
        doc = yaml.safe_load(path.read_text())
    elif path.suffix == ".json":
        doc = json.loads(path.read_text())
    else:
        raise ValueError(f"Unsupported file type: {path}")
    return normalize_doc(doc)


def normalize_doc(doc):
    """Convert datetime objects (from YAML timestamps) to ISO strings for schema validation."""
    import datetime
    if isinstance(doc, dict):
        return {k: normalize_doc(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [normalize_doc(v) for v in doc]
    if isinstance(doc, (datetime.datetime, datetime.date)):
        return doc.isoformat()
    return doc


def detect_kind(path: Path):
    name = path.name
    # Never treat .github/workflows or schemas as runbooks
    if ".github" in path.parts or path.parent.name == "schemas":
        return None
    if name == "manifest.yaml" or name == "manifest.yml":
        return "manifest"
    if name.endswith(".yaml") or name.endswith(".yml"):
        return "runbook"
    if name.endswith(".json") and "attestations" in path.parts:
        return "attestation"
    if name == "index.json" and str(path).endswith("registry/index.json"):
        return "registry"
    return None


def check_repo_path(path: Path, kind: str, repo: str):
    """Runbooks must live under runbooks/github.com/<owner>/<repo>."""
    if kind != "runbook":
        return
    if not repo or "/" not in repo:
        FAILURES.append(f"[{path}] runbook missing/invalid repo field")
        return
    expected = ROOT / "runbooks" / "github.com" / repo
    actual = str(path.resolve()) if not path.is_absolute() else str(path)
    if not actual.startswith(str(expected.resolve())):
        FAILURES.append(f"[{path}] runbook path does not match repo {repo}")


def validate(path: Path):
    kind = detect_kind(path)
    if not kind:
        WARNINGS.append(f"[{path}] unrecognized file kind, skipped")
        return
    try:
        doc = load_doc(path)
    except Exception as e:
        FAILURES.append(f"[{path}] failed to parse: {e}")
        return

    schema = SCHEMAS.get(kind)
    if schema:
        try:
            jsonschema_validate(doc, schema)
        except jsonschema.ValidationError as e:
            FAILURES.append(f"[{path}] schema error: {e.message}")

    # Cross-field checks
    if kind == "runbook":
        repo = f"{doc.get('repo', {}).get('owner', '')}/{doc.get('repo', {}).get('name', '')}"
        check_repo_path(path, kind, repo)


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["."]
    files = []
    for t in targets:
        p = Path(t)
        if not p.exists():
            FAILURES.append(f"[{t}] does not exist")
            continue
        if p.is_dir():
            for pattern in ("*.yaml", "*.yml", "*.json"):
                files.extend(p.rglob(pattern))
        else:
            files.append(p)

    for f in sorted(files):
        validate(f)

    for w in WARNINGS:
        print(f"WARN: {w}")
    for f in FAILURES:
        print(f"FAIL: {f}")

    print(f"\nValidated {len(files)} file(s); {len(WARNINGS)} warning(s), {len(FAILURES)} failure(s).")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
