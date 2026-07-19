"""Validate every registry entry, and build the index the app fetches.

Run in CI on each PR. Checks the entry's own shape, then clones the repo at the pinned tag and runs
the *same* manifest validation and security scan the app runs at install time - so a submission that
would be blocked on a user's machine is blocked here instead.

    python scripts/validate.py            # validate only
    python scripts/validate.py --build    # also write index.json
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).parent.parent / "registry"
INDEX = Path(__file__).parent.parent / "index.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
REQUIRED = ("id", "name", "description", "repo")


def fail(problems: list[str]) -> None:
    for problem in problems:
        print(f"::error::{problem}")
    sys.exit(1)


def check_entry(path: Path) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {}, [f"{path.name}: invalid JSON ({error})"]
    if not isinstance(entry, dict):
        return {}, [f"{path.name}: must be a JSON object"]

    for field in REQUIRED:
        if not entry.get(field):
            problems.append(f"{path.name}: '{field}' is required")

    entry_id = str(entry.get("id", ""))
    if entry_id and not ID_RE.match(entry_id):
        problems.append(f"{path.name}: id must be lowercase letters, digits and dashes")
    if entry_id and path.stem != entry_id:
        problems.append(f"{path.name}: filename must match the id ({entry_id}.json)")

    repo = str(entry.get("repo", ""))
    if repo and not repo.startswith("https://"):
        problems.append(f"{path.name}: repo must be an https URL")

    return entry, problems


def check_repo(entry: dict[str, Any]) -> list[str]:
    """Clone at the newest release tag and run the app's own manifest + security checks.

    A listing floats: it names the repository, and the version comes from its tags. So this
    validates whatever the author has published most recently, not a version pinned here.
    """
    try:
        from inline_core.extensions.fetch import latest_tag
        from inline_core.extensions.manifest import ManifestError, load_manifest
        from inline_core.extensions.scanner import Severity, scan
    except ImportError:
        print("::warning::inline-core has no extension support; skipping the deep check")
        return []

    entry_id, repo = str(entry["id"]), str(entry["repo"])
    tag = str(entry.get("pin") or latest_tag(repo) or "")
    if not tag:
        return [f"{entry_id}: {repo} has no release tag; the author must tag a release first"]
    print(f"{entry_id}: validating {tag}")
    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / entry_id
        clone = subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", tag, repo, str(checkout)],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone.returncode != 0:
            return [f"{entry_id}: could not clone {repo} at {tag} ({clone.stderr.strip()})"]

        try:
            manifest = load_manifest(checkout, expect_id=entry_id)
        except ManifestError as error:
            return [f"{entry_id}: {problem}" for problem in error.problems]

        report = scan(checkout, manifest)
        problems = [
            f"{entry_id}: {f.rule} - {f.message} ({f.file}:{f.line})"
            for f in report.by_severity(Severity.CRITICAL)
        ]
        for finding in report.findings:
            if finding.severity in (Severity.HIGH, Severity.MEDIUM):
                print(
                    f"::warning::{entry_id}: {finding.rule} - {finding.message} "
                    f"({finding.file}:{finding.line}) - users must approve this at install"
                )
        return problems


def main() -> None:
    entries: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[str] = set()

    for path in sorted(REGISTRY.glob("*.json")):
        entry, entry_problems = check_entry(path)
        problems.extend(entry_problems)
        if entry_problems:
            continue
        entry_id = str(entry["id"])
        if entry_id in seen:
            problems.append(f"{path.name}: duplicate id {entry_id!r}")
            continue
        seen.add(entry_id)
        problems.extend(check_repo(entry))
        entries.append(entry)

    if problems:
        fail(problems)

    print(f"{len(entries)} extension(s) validated")
    if "--build" in sys.argv:
        INDEX.write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {INDEX.name}")


if __name__ == "__main__":
    main()
