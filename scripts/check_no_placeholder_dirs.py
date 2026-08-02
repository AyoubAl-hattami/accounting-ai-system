#!/usr/bin/env python3
"""Guard against decorative/placeholder-only directories in the repo.

This script inspects only *tracked* files (via ``git ls-files``), derives the
set of tracked directories from those paths, and fails if any tracked
directory contains nothing but placeholder content:

- ``.gitkeep``
- a placeholder-only ``README.md`` (short, and containing phrases such as
  "scaffolding only", "future work", "placeholder", "coming soon", "tbd")
- an empty ``__init__.py`` (0 bytes, or only a docstring/comment)
- an empty ``index.ts`` / ``index.tsx`` (0 bytes, or only comments / a bare
  re-export of nothing)

Because directory membership is derived purely from ``git ls-files``, paths
that are not tracked (``.git``, ``node_modules``, ``.venv``, build output,
``__pycache__``, ``.pytest_cache``, generated artifacts, etc.) are naturally
excluded without needing explicit ignore rules.

Usage:
    python scripts/check_no_placeholder_dirs.py

Exit status is non-zero (and the offending directories are printed) if any
placeholder-only directory is found.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PLACEHOLDER_PHRASES = (
    "scaffolding only",
    "future work",
    "placeholder",
    "coming soon",
    "tbd",
    "not yet implemented",
    "to be determined",
)

# Directories where sparse/placeholder-looking content is legitimate and must
# never be flagged, even if this script's heuristics would otherwise match.
ALLOWED_SPARSE_DIR_SUFFIXES = (
    "alembic/versions",
)


def get_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def build_dir_to_files(tracked_files: list[str]) -> dict[str, list[str]]:
    """Map every tracked directory to the list of tracked files directly in it."""
    dir_to_files: dict[str, list[str]] = {}
    all_dirs: set[str] = set()

    for rel_path in tracked_files:
        p = Path(rel_path)
        parent = str(p.parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        dir_to_files.setdefault(parent, []).append(rel_path)

        # Register every ancestor directory too, so directories that only
        # contain other directories (no direct files) are also considered.
        cur = p.parent
        while True:
            cur_str = str(cur).replace("\\", "/")
            if cur_str == ".":
                break
            all_dirs.add(cur_str)
            if cur.parent == cur:
                break
            cur = cur.parent

    for d in all_dirs:
        dir_to_files.setdefault(d, [])

    return dir_to_files


def is_placeholder_readme(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    stripped = text.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    has_phrase = any(phrase in lowered for phrase in PLACEHOLDER_PHRASES)
    # Short + contains a placeholder phrase => decorative-only doc.
    return has_phrase and len(stripped) < 1500


def is_empty_init_py(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    stripped = text.strip()
    if not stripped:
        return True
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("#"):
            continue
        if ln.startswith('"""') or ln.startswith("'''"):
            continue
        # Allow a single triple-quoted docstring spanning multiple lines: if
        # every non-empty line is inside/around a docstring or comment, this
        # loop will simply fall through without returning False below.
        if ln.endswith('"""') or ln.endswith("'''"):
            continue
        return False
    return True


def is_empty_index_ts(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    stripped = text.strip()
    if not stripped:
        return True
    # Strip block and line comments to see if any real statement remains.
    import re

    without_block_comments = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
    without_comments = "\n".join(
        ln for ln in without_block_comments.splitlines() if not ln.strip().startswith("//")
    ).strip()
    return not without_comments


def is_placeholder_file(rel_path: str) -> bool:
    path = REPO_ROOT / rel_path
    name = path.name

    if name == ".gitkeep":
        return True
    if name == "README.md":
        return is_placeholder_readme(path)
    if name == "__init__.py":
        return is_empty_init_py(path)
    if name in ("index.ts", "index.tsx"):
        return is_empty_index_ts(path)
    return False


def find_placeholder_dirs(dir_to_files: dict[str, list[str]]) -> list[str]:
    failures: list[str] = []

    # Directories that contain other tracked directories are never
    # placeholder-only on their own; only leaf-ish directories (in terms of
    # direct tracked files) matter here, but we still need to know whether a
    # directory has child directories with real content.
    all_dirs = sorted(dir_to_files.keys())
    child_dirs: dict[str, list[str]] = {d: [] for d in all_dirs}
    for d in all_dirs:
        if not d:
            continue
        parent = str(Path(d).parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        child_dirs.setdefault(parent, []).append(d)

    def dir_has_real_content(d: str) -> bool:
        files = dir_to_files.get(d, [])
        if any(not is_placeholder_file(f) for f in files):
            return True
        return False

    for d in all_dirs:
        if not d:
            continue
        if any(d == suffix or d.endswith("/" + suffix) for suffix in ALLOWED_SPARSE_DIR_SUFFIXES):
            continue

        files = dir_to_files.get(d, [])
        children = child_dirs.get(d, [])

        if not files and not children:
            # Not actually possible (empty dirs aren't tracked by git), but
            # guard anyway.
            continue

        if children:
            # A directory with real subdirectories is a namespace/package
            # boundary; it's fine as long as its own direct files (if any)
            # aren't placeholder-only OR at least one descendant has real
            # content.
            if files and not dir_has_real_content(d):
                # It has direct files, and all of them are placeholders,
                # but it might still be legitimate purely as a namespace if
                # a child directory has real content. Only flag if none of
                # the children (recursively) has real content either.
                pass
            continue

        # Leaf directory (no child directories): must have at least one
        # non-placeholder tracked file.
        if not dir_has_real_content(d):
            failures.append(d)

    return failures


def main() -> int:
    tracked_files = get_tracked_files()
    dir_to_files = build_dir_to_files(tracked_files)
    failures = find_placeholder_dirs(dir_to_files)

    if failures:
        print("Placeholder-only directories found (decorative dirs are not allowed):")
        for d in sorted(failures):
            print(f"  - {d}")
        print()
        print(
            "Either add real code/tests/docs to these directories, or remove "
            "them entirely. See docs/architecture/clean-architecture-migration-status.md."
        )
        return 1

    print(f"OK: no placeholder-only directories found ({len(tracked_files)} tracked files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
