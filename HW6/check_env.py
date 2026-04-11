"""
Verify Python imports, FFmpeg/ffprobe, and Poppler (pdftoppm) for this project.
Run from the project root: python check_env.py
"""

import importlib.util
import os
import shutil
import sys

from utils.ffmpeg_bin import resolve_ffprobe_exe, resolve_ffmpeg_exe
from utils.poppler_path import resolve_poppler_bin


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _fail(msg: str) -> None:
    print(f"[MISSING] {msg}")


def main() -> int:
    ok = True

    for mod, pip_hint in (
        ("google.generativeai", "google-generativeai"),
        ("pdf2image", "pdf2image"),
        ("ffmpeg", "ffmpeg-python"),
    ):
        if importlib.util.find_spec(mod) is None:
            _fail(f"Python package `{pip_hint}` not found. Run: pip install -r requirements.txt")
            ok = False
        else:
            _ok(f"Python import: {mod}")

    if importlib.util.find_spec("edge_tts") is None:
        print(
            "[INFO] edge-tts not installed — run: pip install edge-tts for spoken MP3. "
            "Or set TTS_PROVIDER=mock for placeholder tones only."
        )
    else:
        _ok("Python import: edge_tts")

    ff = shutil.which("ffmpeg") or resolve_ffmpeg_exe()
    if ff:
        _ok(f"ffmpeg -> {ff}")
    else:
        _fail(
            "ffmpeg not on PATH and not auto-discovered. Windows: winget install Gyan.FFmpeg "
            "or set FFMPEG_PATH to ffmpeg.exe."
        )
        ok = False

    fp = shutil.which("ffprobe") or resolve_ffprobe_exe()
    if fp:
        _ok(f"ffprobe -> {fp}")
    else:
        _fail(
            "ffprobe not on PATH and not auto-discovered. Install FFmpeg (includes ffprobe) "
            "or set FFPROBE_PATH."
        )
        ok = False

    pdftoppm = shutil.which("pdftoppm")
    discovered = resolve_poppler_bin()
    if pdftoppm:
        _ok(f"pdftoppm (Poppler) -> {pdftoppm}")
    elif discovered:
        pp = os.path.join(discovered, "pdftoppm.exe")
        _ok(f"pdftoppm (Poppler) -> {pp} (auto-discovered; restart terminal to refresh PATH)")
    else:
        _fail(
            "Poppler not found. Windows: winget install oschwartz10612.Poppler, then restart the "
            "terminal or set POPPLER_PATH to the ...\\Library\\bin folder (see README)."
        )
        ok = False

    if ok:
        print("\nEnvironment looks ready for style_agent.py and pipeline.py.")
        return 0
    print("\nFix the items above, then run this script again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
