"""Validate the release contract: strict SemVer version in mod.txt and a matching tag.

Contract (v1.0.0 onward):
  - mod.txt "version" must be exactly MAJOR.MINOR.PATCH.
  - Each component is a non-negative integer with no leading zero (except "0").
  - No pre-release suffix, no build metadata, no extra text.
  - The git tag must be exactly "v" + the mod.txt version.

The release workflow invokes this module so CI and local checks share one
source of truth, covered by unit tests.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Strict SemVer (MAJOR.MINOR.PATCH only, no pre-release, no build metadata,
# no leading zeros on any numeric component).
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
# Tag = "v" followed by the same strict SemVer.
TAG_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def validate_mod_version(version: str) -> tuple[bool, str]:
    """Return (ok, message). Message is empty on success."""
    if not isinstance(version, str):
        return False, f"mod.txt version is not a string (got {type(version).__name__})."
    if not SEMVER_RE.match(version):
        return False, (
            f"mod.txt version '{version}' is not a valid SemVer "
            f"(must be MAJOR.MINOR.PATCH with no leading zeros and no suffix)."
        )
    return True, ""


def validate_tag(tag: str, mod_version: str) -> tuple[bool, str]:
    """Return (ok, message). The tag must equal 'v' + mod_version."""
    if not isinstance(tag, str):
        return False, f"tag is not a string (got {type(tag).__name__})."
    expected = f"v{mod_version}"
    if tag != expected:
        return False, (
            f"Release tag '{tag}' does not match mod.txt version "
            f"'{mod_version}'. Expected '{expected}'."
        )
    if not TAG_RE.match(tag):
        return False, (
            f"Release tag '{tag}' is not a valid SemVer tag "
            f"(must be vMAJOR.MINOR.PATCH without leading zeros or suffix)."
        )
    return True, ""


def validate_pair(tag: str, mod_version: str) -> tuple[bool, str]:
    ok_v, msg_v = validate_mod_version(mod_version)
    if not ok_v:
        return False, msg_v
    return validate_tag(tag, mod_version)


def read_mod_version(mod_txt_path: Path) -> str:
    data = json.loads(mod_txt_path.read_text(encoding="utf-8"))
    return data["version"]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            f"usage: {argv[0]} <tag> <mod.txt>",
            file=sys.stderr,
        )
        return 2
    tag = argv[1]
    mod_path = Path(argv[2])
    try:
        mod_version = read_mod_version(mod_path)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"unable to read mod.txt: {exc}", file=sys.stderr)
        return 2

    ok, message = validate_pair(tag, mod_version)
    if not ok:
        print(message, file=sys.stderr)
        return 1
    print(f"ok: tag={tag} matches mod.txt version={mod_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
