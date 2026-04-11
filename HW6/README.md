# Agentic video pipeline

Python pipeline that turns a lecture PDF into slide images, Gemini-powered descriptions, premise and narrative arc, slide narrations matched to a style profile, **Edge TTS** MP3 audio (or optional placeholder tones), and a final assembled video.

**Repository policy:** source code and JSON artifacts are tracked. Generated **images**, **audio**, and **video** files are **not** committed (see `.gitignore`).

## Requirements

- **Python** 3.10+
- **FFmpeg** and **ffprobe** on your `PATH`
- **Poppler** (`pdftoppm`) on your `PATH`, *or* set **`POPPLER_PATH`** to Poppler’s `bin` folder (common on Windows)

## Quick install

```bash
pip install google-generativeai pdf2image ffmpeg-python Pillow
```

Or install the pinned set:

```bash
pip install -r requirements.txt
```

### FFmpeg and Poppler on PATH

- **Verify:** from the project root run `python check_env.py`. It checks Python packages, `ffmpeg` / `ffprobe`, and `pdftoppm`.

- **Windows (examples):**
  - FFmpeg: [Gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/) or `winget install Gyan.FFmpeg` (add the `bin` directory to PATH).
  - Poppler: install a [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) build and add its `Library\bin` (or `bin`) folder to PATH, **or** set `POPPLER_PATH` to that folder so `pipeline.py` can find it without a global PATH change:

    ```powershell
    $env:POPPLER_PATH = "C:\path\to\poppler\Library\bin"
    ```

- **macOS:** `brew install ffmpeg poppler`

- **Linux:** use your package manager (e.g. `ffmpeg`, `poppler-utils`).

## API key

Set **one** of:

- `GOOGLE_API_KEY`, or
- `GEMINI_API_KEY`

Example (PowerShell):

```powershell
$env:GOOGLE_API_KEY = "your-key-here"
```

On **Windows**, if FFmpeg is installed but not on PATH, the pipeline auto-detects the WinGet install, or you can set **`FFMPEG_PATH`** / **`FFPROBE_PATH`** to the full paths of `ffmpeg.exe` and `ffprobe.exe`.

Gemini **model IDs** change over time. Defaults are **`gemini-2.5-flash`** (style, slides, premise, arc) and **`gemini-2.5-pro`** (narration). Older IDs like `gemini-2.0-flash` may be unavailable to new keys. If you get “model not found,” set overrides (use names from [Google AI Studio](https://aistudio.google.com/) → your API):

```powershell
$env:GEMINI_MODEL_FLASH = "gemini-2.5-flash"
$env:GEMINI_MODEL_PRO = "gemini-2.5-flash"
```

## Generate `style.json` (once)

With the default transcript file in the working directory:

```bash
python style_agent.py
```

Custom paths:

```bash
python style_agent.py path/to/transcript.txt -o style.json
```

The repo includes a sample **`lecture_transcript.txt`** and a sample **`style.json`** so you can run the pipeline without calling Gemini first.

## Run the full pipeline

Place your lecture PDF where you want (e.g. next to `pipeline.py`) and run:

```bash
python pipeline.py --pdf Lecture_17_AI_screenplays.pdf --style style.json
```

Defaults match the above if you omit flags:

```bash
python pipeline.py
```

Outputs go under `projects/project_YYYYMMDD_HHMM/`: JSON (tracked), plus ignored `slide_images/`, `audio/`, and the `.mp4` file.

**Speech audio:** by default the pipeline uses **Microsoft Edge TTS** via **`edge-tts`** (install with `pip install edge-tts`). It writes real MP3 narration per slide. To force the old FFmpeg sine-wave placeholder only, set `TTS_PROVIDER=mock`. Optional: `EDGE_TTS_VOICE` (default `en-US-AriaNeural`).

## JSON layout

| Path | Role |
|------|------|
| `style.json` | Style profile (repo root; from `style_agent.py`). |
| `projects/<id>/slide_description.json` | Array of strings: full description per slide (prior-slide chaining in the agent). |
| `projects/<id>/premise.json` | Structured: `thesis`, `hook`, `audience`, `deck_grounding`, `premise`. |
| `projects/<id>/arc.json` | `arc` string plus optional `slide_beats` array. |
| `projects/<id>/slide_description_narration.json` | Array of `{slide_index, description, narration}`. |

See **`projects/example_project/`** for example JSON in that shape.

### Rubric alignment

| Component | Implementation |
|-----------|----------------|
| Style file | `style_agent.py` → **`style.json`** at repo root from transcript. |
| Slide descriptions | Current slide image + **full prior descriptions** → **`slide_description.json`**. |
| Premise | Entire slide list → structured **`premise.json`**. |
| Arc | **premise.json** + full slide list → **`arc.json`**. |
| Narration | Image + style + premise + arc + full deck + **prior narrations**; title slide intro/overview → **`slide_description_narration.json`**. |
| Audio | **`audio/slide_NNN.mp3`** via **edge-tts** (or `TTS_PROVIDER=mock` for FFmpeg tones). |
| Video | **`slide_images/`** + **`audio/`** by index; segment length from audio duration; **`<pdf_stem>.mp4`**. |
| Repo | Code + JSON + README; **`.gitignore`** on generated media. |

## Upload to GitHub

Configure your Git author once (if you have not already):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

This repository may already have an initial commit. To push it, create an empty repository on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git branch -M main
git push -u origin main
```

If you need a fresh repo locally instead:

```bash
git init
git add .
git status
git commit -m "Initial commit: agentic video pipeline"
```

Do not commit API keys, `.env`, or generated media (already covered by `.gitignore`).
