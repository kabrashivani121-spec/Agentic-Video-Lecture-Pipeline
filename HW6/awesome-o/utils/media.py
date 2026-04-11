import asyncio
import os
import tempfile

import ffmpeg

from utils.ffmpeg_bin import resolve_ffmpeg_exe, resolve_ffprobe_exe


class TextToSpeech:
    """
    Writes audio/slide_NNN.mp3 per slide from narration text.

    Default: Microsoft Edge TTS (edge-tts, no API key). Override with env TTS_PROVIDER=mock
    for the FFmpeg sine placeholder only.
    """

    def synthesize_batch(self, narrations, audio_dir):
        ffmpeg_exe = resolve_ffmpeg_exe()
        if not ffmpeg_exe:
            raise RuntimeError(
                "ffmpeg not found. Install FFmpeg (e.g. winget install Gyan.FFmpeg), "
                "restart the terminal, or set FFMPEG_PATH to the full path of ffmpeg.exe."
            )

        paths = []
        for entry in narrations:
            idx = entry["slide_index"]
            text = (entry.get("narration") or "").strip() or "."
            path = os.path.join(audio_dir, f"slide_{idx:03d}.mp3")
            self._write_slide_mp3(text, path, ffmpeg_exe)
            if not os.path.isfile(path) or os.path.getsize(path) < 1:
                raise RuntimeError(f"TTS produced no usable audio: {path}")
            print(f"  {path} ({os.path.getsize(path)} bytes)")
            paths.append(path)
        return paths

    def _write_slide_mp3(self, text: str, path: str, ffmpeg_exe: str) -> None:
        provider = os.environ.get("TTS_PROVIDER", "edge").strip().lower()
        if provider == "mock":
            self._mock_tts(text, path, ffmpeg_exe)
            return
        if provider in ("edge", "auto"):
            try:
                import edge_tts

                voice = os.environ.get("EDGE_TTS_VOICE", "en-US-AriaNeural")

                async def _save() -> None:
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(path)

                asyncio.run(_save())
                return
            except ImportError:
                if provider == "edge":
                    raise RuntimeError(
                        'TTS_PROVIDER=edge requires the edge-tts package. Run: pip install edge-tts'
                    ) from None
            except Exception as exc:
                if provider == "edge":
                    raise RuntimeError(f"edge-tts failed: {exc}") from exc
                print(f"Warning: edge-tts failed ({exc}); using placeholder tone for this run.")
        self._mock_tts(text, path, ffmpeg_exe)

    def _merge_mp3_parts(self, part_paths, out_path, ffmpeg_exe: str):
        """Concatenate MP3 parts with ffmpeg concat demuxer (same codec stream)."""
        tmp = tempfile.mkdtemp(prefix="tts_merge_")
        lst = None
        try:
            lst = os.path.join(tmp, "audio_concat.txt")
            with open(lst, "w", encoding="utf-8") as f:
                for p in part_paths:
                    f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
            (
                ffmpeg.input(lst, format="concat", safe=0)
                .output(out_path, acodec="copy")
                .overwrite_output()
                .run(quiet=True, cmd=ffmpeg_exe)
            )
        finally:
            if lst:
                try:
                    os.remove(lst)
                except OSError:
                    pass
            try:
                os.rmdir(tmp)
            except OSError:
                pass

    def _mock_tts(self, text: str, path: str, ffmpeg_exe: str) -> None:
        """Placeholder tone when edge-tts is unavailable or TTS_PROVIDER=mock."""
        duration = min(8.0, max(1.0, len(text) / 12.0))
        try:
            (
                ffmpeg.input(f"sine=frequency=440:duration={duration}", f="lavfi")
                .output(path, acodec="libmp3lame", audio_bitrate="128k")
                .overwrite_output()
                .run(quiet=True, cmd=ffmpeg_exe)
            )
        except ffmpeg.Error as e:
            err = (e.stderr.decode() if getattr(e, "stderr", None) else str(e))
            raise RuntimeError(
                f"FFmpeg could not write MP3 to {path}. {err}"
            ) from e
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Could not run FFmpeg at {ffmpeg_exe!r}. Fix PATH or set FFMPEG_PATH. {e}"
            ) from e


class VideoAssembler:
    """
    One segment per slide: PNG + matching MP3 index. Segment length equals probed audio duration
    (no extra still time after speech — video track is trimmed to audio length).
    """

    @staticmethod
    def assemble(image_paths, audio_paths, final_name):
        if len(image_paths) != len(audio_paths):
            raise ValueError("image_paths and audio_paths must have the same length")

        ffmpeg_exe = resolve_ffmpeg_exe()
        ffprobe_exe = resolve_ffprobe_exe()
        if not ffmpeg_exe:
            raise RuntimeError(
                "ffmpeg not found. Install FFmpeg or set FFMPEG_PATH to ffmpeg.exe."
            )
        if not ffprobe_exe:
            raise RuntimeError(
                "ffprobe not found. Install FFmpeg (ffprobe is beside ffmpeg) or set FFPROBE_PATH."
            )

        tmp = tempfile.mkdtemp(prefix="agentic_video_")
        parts: list[str] = []
        try:
            for i, (img, aud) in enumerate(zip(image_paths, audio_paths)):
                part_path = os.path.join(tmp, f"part_{i:04d}.mp4")
                probed = ffmpeg.probe(aud, cmd=ffprobe_exe)
                dur_raw = probed.get("format", {}).get("duration")
                duration = float(dur_raw) if dur_raw not in (None, "") else 0.0
                if duration <= 0:
                    raise ValueError(f"Could not read duration for audio file: {aud}")
                video = ffmpeg.input(img, loop=1, framerate=25, t=duration)
                audio = ffmpeg.input(aud)
                (
                    ffmpeg.output(
                        video,
                        audio,
                        part_path,
                        vcodec="libx264",
                        acodec="aac",
                        pix_fmt="yuv420p",
                        shortest=1,
                    )
                    .overwrite_output()
                    .run(quiet=True, cmd=ffmpeg_exe)
                )
                parts.append(part_path)

            list_path = os.path.join(tmp, "concat_list.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for p in parts:
                    f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")

            (
                ffmpeg.input(list_path, format="concat", safe=0)
                .output(final_name, c="copy")
                .overwrite_output()
                .run(quiet=True, cmd=ffmpeg_exe)
            )
        finally:
            for p in parts:
                try:
                    os.remove(p)
                except OSError:
                    pass
            try:
                os.remove(os.path.join(tmp, "concat_list.txt"))
            except OSError:
                pass
            try:
                os.rmdir(tmp)
            except OSError:
                pass
