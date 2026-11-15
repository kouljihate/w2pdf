"""Bump the W2PDF version everywhere it is written.

The version lives in one place conceptually — ``w2pdf/__init__.py`` — but it is
also mirrored in the Dockerfile label, the README badge and the changelog. This
script updates all four at once so a release never drifts.

Usage::

    python scripts/bump_version.py patch "Fix the date filter"
    python scripts/bump_version.py minor "Add output folder"
    python scripts/bump_version.py 2.0.0 "Rewrite the layout engine"

Afterwards review the diff, then commit and tag with the printed command.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = ROOT / "w2pdf" / "__init__.py"
DOCKERFILE = ROOT / "Dockerfile"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(r'__version__\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')

KINDS = ("major", "minor", "patch")


def read_version() -> tuple[int, int, int]:
    match = VERSION_RE.search(INIT_FILE.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"No __version__ found in {INIT_FILE}")
    return tuple(int(part) for part in match.group("version").split("."))  # type: ignore[return-value]


def next_version(current: tuple[int, int, int], kind: str) -> str:
    major, minor, patch = current
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump the W2PDF version.")
    parser.add_argument("kind", help="major, minor, patch, or an explicit X.Y.Z version")
    parser.add_argument("note", help="one-line changelog entry describing the change")
    args = parser.parse_args()

    current_parts = read_version()
    current = ".".join(str(part) for part in current_parts)

    if args.kind in KINDS:
        new = next_version(current_parts, args.kind)
    elif re.fullmatch(r"\d+\.\d+\.\d+", args.kind):
        new = args.kind
    else:
        raise SystemExit(f"'{args.kind}' is not one of {', '.join(KINDS)} or X.Y.Z")

    if new == current:
        raise SystemExit(f"Version is already {new}")

    # w2pdf/__init__.py
    INIT_FILE.write_text(
        VERSION_RE.sub(f'__version__ = "{new}"', INIT_FILE.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    # Dockerfile label
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    DOCKERFILE.write_text(
        re.sub(r"ARG APP_VERSION=[\d.]+", f"ARG APP_VERSION={new}", dockerfile),
        encoding="utf-8",
    )

    # README badge
    readme = README.read_text(encoding="utf-8")
    README.write_text(
        re.sub(r"badge/version-[\d.]+-", f"badge/version-{new}-", readme),
        encoding="utf-8",
    )

    # Changelog: newest section goes directly under the intro.
    changelog = CHANGELOG.read_text(encoding="utf-8")
    section = f"## {new} — {date.today():%Y-%m-%d}\n\n- {args.note.strip()}\n\n"
    if f"## {new} " in changelog:
        raise SystemExit(f"CHANGELOG.md already has a section for {new}")
    first_section = re.search(r"^## ", changelog, flags=re.MULTILINE)
    if first_section is None:
        changelog = changelog.rstrip() + "\n\n" + section
    else:
        index = first_section.start()
        changelog = changelog[:index] + section + changelog[index:]
    CHANGELOG.write_text(changelog, encoding="utf-8")

    print(f"{current} -> {new}")
    print('Next: git add -A && git commit -m "..." && git tag -a v%s -m "W2PDF v%s" && git push origin main v%s' % (new, new, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
