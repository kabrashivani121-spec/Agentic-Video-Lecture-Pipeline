# Awesome-O

Classroom-scale **screenplay pipeline**: chat agents and batch scripts build **premise → arc → sequences → scenes**, with optional **dialogue repair** and a **rewrite** pass. Outputs are JSON files under a project folder (e.g. `projects/midnight_run_20260401_221032/` — slug from a Gemini-chosen title plus UTC timestamp).

This repo also includes a **lecture video pipeline** that turns a **PDF deck** into slide images, Gemini descriptions, premise/arc for narration, slide scripts, placeholder audio, and an **MP4** (see [Lecture video pipeline](#lecture-video-pdf--narrated-video)).

Architecture slides for lecture: **`awesome_o_architecture_slides.html`** (open in a browser).

---

## Requirements

- **Python 3.11+**
- **Google Gemini** API access (default model: `gemini-2.5-flash` via pydantic-ai for the screenplay tools; the lecture video pipeline uses `google-generativeai` with models named in `utils/agents.py` / `style_agent.py`).
- **Lecture video only:** **FFmpeg** / **ffprobe** and **Poppler** (`pdftoppm`) on your `PATH`, or set **`POPPLER_PATH`** to Poppler’s `bin` folder (Windows). Verify with `python check_env.py`.

---

## Environment (`.env`)

Put a **`.env`** file in the **repo root** (next to `requirements.txt`). It is loaded automatically (`python-dotenv`) for the **`awesome_o`** screenplay runners.

| Variable | Notes |
|----------|--------|
| **`GEMINI_API_KEY`** | Primary; use your key from Google AI Studio / Gemini API. |
| **`GOOGLE_API_KEY`** | Alternative name; either works with the Google provider. |
| **`AWESOME_O_MODEL`** | Optional override, e.g. `google-gla:gemini-2.5-flash`. |

Copy **`.env.example`** → `.env` and paste your key. Do not commit `.env`.

The **lecture video** scripts (`style_agent.py`, `pipeline.py`) read **`GOOGLE_API_KEY`** or **`GEMINI_API_KEY`** from the environment (or configure the same keys in code paths that call `google.generativeai`).

**Lecture video Gemini models:** defaults are **`gemini-2.5-flash`** (style, slides, premise, arc) and **`gemini-2.5-pro`** (narration). Older IDs (e.g. `gemini-2.0-flash`) may be unavailable to new API keys. If you see `404 model … not found`, set **`GEMINI_MODEL_FLASH`** and **`GEMINI_MODEL_PRO`** (e.g. both to `gemini-2.5-flash`).

---

## Install (repo root)

Open a terminal in the **repo root** (the folder that contains `requirements.txt` and `awesome_o/`). Install dependencies:

```bash
pip install -r requirements.txt
```

Keep running the `run_*.py` scripts from that same root so `import awesome_o` resolves and paths like `projects\…` work.

**Clone this repo** (if you use GitHub CLI: `gh repo clone zlisto/awesome-o`; otherwise `git clone https://github.com/zlisto/awesome-o.git`).

---

## Agentic flow (screenplay)

```text
premise.json  →  arc.json  →  sequence.json  →  scenes.json
     ↑              ↑              ↑                 ↑
  chat CLI     chat CLI      batch (+opt.      batch (+opt.
  /generate    /draft …       adaptive plan)    scene_plan)
```

Optional afterward (same project folder):

1. **`run_fix_scene_dialogue.py`** — Merge mis-typed dialogue in `scenes.json` (deterministic; add `--llm` if needed).
2. **`run_scenes_rewrite.py`** — New file **`scenes_rewrite.json`**: polish using premise + arc + `sequence.json` + prior scenes in the same sequence (and a tail from the previous sequence). Original `scenes.json` is left unchanged.

---

## How to run (class)

From the **repo root**, run **`python run_….py …`**. Each runner forwards **`sys.argv[1:]`** into **`argparse`** inside `awesome_o.cli.*` (use **`python run_….py --help`** for flags).

**Windows:** If double-clicking `.py` opens an editor, run from a terminal: **`python run_….py`**.

| Step | Runner | What it does |
|------|--------|----------------|
| 1. Premise | `python run_premise_agent.py` | Chat; `/generate` asks Gemini for a movie-style title, then writes `projects/<title_slug>_<UTC_datetime>/premise.json`. |
| 2. Arc | `python run_arc_agent.py --project projects\<id>` | Chat; `/draft`, `/edit`, `/show`, `/target`, `/runtime` → `arc.json`. |
| 3. Sequences | `python run_sequence_agent.py --project projects\<id>` | Writes `sequence.json` (default 8 rows; resumes if the file exists). |
| 4. Scenes | `python run_scenes_agent.py --project projects\<id>` | Writes `scenes.json` (`--per-sequence` or adaptive plan). |
| 5. Fix dialogue | `python run_fix_scene_dialogue.py --project projects\<id>` | Fixes `scenes.json` in place; optional `--llm`. |
| 6. Rewrite | `python run_scenes_rewrite.py --project projects\<id>` | Writes **`scenes_rewrite.json`**. |

---

## Lecture video (PDF → narrated video)

Independent of the screenplay chat flow. It rasterizes a PDF, calls Gemini for slide text and narration, writes JSON under `projects/project_YYYYMMDD_HHMM/`, and assembles an MP4. **Committed artifacts:** Python + JSON examples; **not committed:** generated PNG, MP3, MP4 (see `.gitignore`).

### Quick install (lecture video stack)

```bash
pip install google-generativeai pdf2image ffmpeg-python Pillow
```

(Already included if you used `pip install -r requirements.txt`.)

### FFmpeg and Poppler

- Run **`python check_env.py`** from the repo root. It checks imports for `google-generativeai`, `pdf2image`, `ffmpeg-python`, and the **`ffmpeg`** / **ffprobe** / **pdftoppm** executables.
- **Windows:** [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) on PATH; [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) — add `Library\bin` to PATH, or:

  ```powershell
  $env:POPPLER_PATH = "C:\path\to\poppler\Library\bin"
  ```

- **macOS:** `brew install ffmpeg poppler` · **Linux:** install `ffmpeg` and `poppler-utils` via your package manager.

### Generate `style.json` from a transcript

```bash
python style_agent.py
```

Defaults: input `lecture_transcript.txt`, output `style.json`. The repo includes sample **`lecture_transcript.txt`** and **`style.json`**.

```bash
python style_agent.py path/to/transcript.txt -o style.json
```

### Run the full video pipeline

Place your lecture PDF (e.g. `Lecture_17_AI_screenplays.pdf`) in the working directory, then:

```bash
python pipeline.py --pdf Lecture_17_AI_screenplays.pdf --style style.json
```

Or use defaults (`Lecture_17_AI_screenplays.pdf`, `style.json`):

```bash
python pipeline.py
```

Outputs: JSON under `projects/<project_id>/`, plus ignored `slide_images/`, `audio/`, and the `.mp4`. Replace the placeholder TTS in `utils/media.py` (`TextToSpeech._mock_tts`) for real voiceover.

### Lecture JSON layout

| Path | Role |
|------|------|
| `style.json` | Style profile for narration (repo root; produced by `style_agent.py`). |
| `projects/<id>/slide_description.json` | Array of strings, one full description per slide (prior-slide chaining in the agent). |
| `projects/<id>/premise.json` | Structured premise: `thesis`, `hook`, `audience`, `deck_grounding`, `premise` (see example). **Different schema** from screenplay `premise.json` in other project folders. |
| `projects/<id>/arc.json` | `arc` (string) plus `slide_beats` (optional array) — consistent with premise + full deck. |
| `projects/<id>/slide_description_narration.json` | Array of `{slide_index, description, narration}`. |

Example shape: **`projects/example_project/`**.

### Rubric alignment (lecture video)

| Component | What this repo does |
|-----------|------------------------|
| **Style file** | `style_agent.py` reads a transcript/caption file and writes **`style.json`** at the repo root (default `-o style.json`). |
| **Slide descriptions** | `SlideAgent` uses each **current slide image** plus **full text of all previous slide descriptions** (real chaining, not a placeholder). Writes **`slide_description.json`**. |
| **Premise** | `PremiseAgent` consumes the **entire** slide-description list and writes structured **`premise.json`**. |
| **Arc** | `ArcAgent` takes **premise.json** + **full slide descriptions** and writes **`arc.json`**. |
| **Narration** | `NarrationAgent` uses **current slide image**, **`style.json`**, premise, arc, **full slide list**, and **all prior narrations** (slide 1 has none). Title slide: **intro + overview** instructions. Output: **`slide_description_narration.json`**. |
| **Audio** | `TextToSpeech` writes **`audio/slide_NNN.mp3`**. Multiple TTS chunks per slide are **merged** into one file. |
| **Video** | `VideoAssembler` pairs **`slide_images/`** PNGs with **`audio/`** MP3s by index; one segment per slide with duration **tied to audio** (no extended still after speech); final **`<pdf_basename>.mp4`** in the project folder. |
| **Repo hygiene** | **`.gitignore`** excludes generated images, audio, and video; **README** documents setup and how to run. |

---

## Package layout (`awesome_o/`)

| Path | Role |
|------|------|
| `models/` | Pydantic types for `premise.json`, `arc.json`, `sequence.json`, `scenes.json`, `scene_plan.json`, etc. |
| `cli/` | Entry points: premise, arc, sequence, scenes, fix_scene_dialogue, scenes_rewrite |
| `persona.py` | System prompts (Awesome-O voice + structured agents) |
| `model_settings.py` | `.env` + default Gemini model id |
| `scene_dialogue_normalize.py` | Rule-based cue+line → `dialogue` merge |

**Lecture video** helpers live at the repo root: `pipeline.py`, `style_agent.py`, `check_env.py`, and **`utils/`** (slide/narration agents + FFmpeg assembly). This is separate from the `awesome_o` package namespace.

---

## Sample data (optional)

- **`projects/terminator_2_20260401_151738/`** — Example JSON from *Terminator 2* (large `scenes.json`). Not produced by the Awesome-O agents; useful as a shape reference.
- **`projects/example_project/`** — Example **lecture-video** JSON (slide descriptions, premise, arc, narrations).

---

## License / course use

Built for MGT575 / class demos; adjust as needed for your syllabus.
