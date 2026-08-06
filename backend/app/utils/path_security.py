"""
Validate server-side file paths for POST /upload/path.

Flow:
  1. Expand ~ and resolve to an absolute path.
  2. Relative paths are resolved against the POC-APP project root.
  3. Reject paths outside allowed roots (project, user home, optional env list).
  4. Return the resolved Path for UploadService to copy into storage/uploads.
"""

import os
from pathlib import Path

from app.utils.paths import BACKEND_ROOT

# POC-APP repo root (parent of backend/).
PROJECT_ROOT = BACKEND_ROOT.parent.resolve()


def _allowed_roots() -> list[Path]:
    """
    Build the list of directory roots under which documents may be read.

    Includes project root, user home, and optional ALLOWED_DOCUMENT_PATH_ROOTS
    (OS path-separated absolute paths).
    """
    roots = [PROJECT_ROOT, Path.home().resolve()]
    extra = os.environ.get("ALLOWED_DOCUMENT_PATH_ROOTS", "").strip()
    if extra:
        for part in extra.split(os.pathsep):
            part = part.strip()
            if part:
                roots.append(Path(part).expanduser().resolve())
    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def _is_under(path: Path, root: Path) -> bool:
    """True if ``path`` is equal to or nested inside ``root``."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_allowed_document_path(raw_path: str) -> Path:
    """
    Parse and authorize a user-supplied path string.

    Raises:
        ValueError: empty path, file missing, or path outside allowed roots.

    Returns:
        Resolved absolute path to an existing file.
    """
    if not raw_path or not raw_path.strip():
        raise ValueError("File path is required")

    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.is_file():
        raise ValueError(f"File not found: {candidate}")

    roots = _allowed_roots()
    if not any(_is_under(candidate, root) for root in roots):
        roots_hint = ", ".join(str(r) for r in roots[:2])
        raise ValueError(
            "Path must be under the POC-APP project folder or your user home directory. "
            f"Allowed roots include: {roots_hint}"
        )

    return candidate
