"""
Resolve the Poppler bin directory for pdf2image on Windows when PATH is stale after winget install.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_poppler_bin() -> str | None:
    """
    Directory containing pdfinfo / pdftoppm for pdf2image's ``poppler_path=``.
    Returns None if only system PATH should be used (and tools must be on PATH).
    """
    explicit = os.environ.get("POPPLER_PATH", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_dir():
            return str(p.resolve())

    w = shutil.which("pdfinfo") or shutil.which("pdftoppm")
    if w:
        return str(Path(w).resolve().parent)

    if os.name != "nt":
        return None

    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None

    winget_pkg = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if winget_pkg.is_dir():
        for candidate in winget_pkg.rglob("pdftoppm.exe"):
            return str(candidate.resolve().parent)

    return None


def poppler_kwargs() -> dict:
    """Keyword args for pdf2image.convert_from_path when Poppler is not on PATH."""
    bin_dir = resolve_poppler_bin()
    if bin_dir:
        return {"poppler_path": bin_dir}
    return {}
