"""
Resolve ffmpeg / ffprobe executables when PATH is stale (e.g. after winget install).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_ffmpeg_exe() -> str | None:
    p = os.environ.get("FFMPEG_PATH", "").strip()
    if p and Path(p).is_file():
        return str(Path(p).resolve())
    w = shutil.which("ffmpeg")
    if w:
        return str(Path(w).resolve())
    if os.name != "nt":
        return None
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None
    pkg = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if not pkg.is_dir():
        return None
    best = None
    for candidate in pkg.rglob("ffmpeg.exe"):
        parent = candidate.parent
        if (parent / "ffprobe.exe").is_file():
            return str(candidate.resolve())
        best = candidate
    if best is not None:
        return str(best.resolve())
    return None


def resolve_ffprobe_exe() -> str | None:
    p = os.environ.get("FFPROBE_PATH", "").strip()
    if p and Path(p).is_file():
        return str(Path(p).resolve())
    w = shutil.which("ffprobe")
    if w:
        return str(Path(w).resolve())
    ffm = resolve_ffmpeg_exe()
    if ffm:
        sib = Path(ffm).parent / "ffprobe.exe"
        if sib.is_file():
            return str(sib.resolve())
    if os.name != "nt":
        return None
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None
    pkg = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if not pkg.is_dir():
        return None
    for candidate in pkg.rglob("ffprobe.exe"):
        return str(candidate.resolve())
    return None
