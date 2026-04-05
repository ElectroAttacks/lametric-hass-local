#!/usr/bin/env python3
"""Bump the version in manifest.json based on the conventional commit message.

Conventional commit rules applied:
  breaking change (! or BREAKING CHANGE footer) -> major
  feat  -> minor
  fix   -> patch
  other -> no bump
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = (
    Path(__file__).parent.parent
    / "custom_components"
    / "lametric_hass_local"
    / "manifest.json"
)

_BREAKING_FOOTER = re.compile(r"^BREAKING[- ]CHANGE:", re.MULTILINE)
_CONV_COMMIT = re.compile(r"^(?P<type>\w+)(?:\([^)]*\))?(?P<bang>!)?: \S")


def _determine_bump(message: str) -> str | None:
    """Return 'major', 'minor', 'patch', or None if no bump is needed."""
    first_line = message.splitlines()[0] if message else ""
    match = _CONV_COMMIT.match(first_line)
    if not match:
        return None

    if match.group("bang") == "!" or _BREAKING_FOOTER.search(message):
        return "major"
    if match.group("type") == "feat":
        return "minor"
    if match.group("type") == "fix":
        return "patch"
    return None


def _bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(p) for p in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    if len(sys.argv) >= 2:
        msg_file = Path(sys.argv[1])
    else:
        msg_file = Path(".git/COMMIT_EDITMSG")

    if not msg_file.exists():
        return 0

    message = msg_file.read_text(encoding="utf-8").strip()
    bump = _determine_bump(message)
    if bump is None:
        return 0

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old_version: str = manifest["version"]
    new_version = _bump_version(old_version, bump)
    manifest["version"] = new_version

    MANIFEST.write_text(json.dumps(manifest, indent=4) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(MANIFEST)], check=True)

    print(f"  manifest version: {old_version} → {new_version} ({bump})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
