import json
import os

import google.generativeai as genai


def _configure():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)


def _flash_model() -> str:
    """Fast model for slides, premise, arc, style. Override: GEMINI_MODEL_FLASH."""
    # gemini-2.0-flash is not offered to new API users; use current generation defaults.
    return os.environ.get("GEMINI_MODEL_FLASH", "gemini-2.5-flash")


def _pro_model() -> str:
    """Stronger model for narrations. Override: GEMINI_MODEL_PRO."""
    return os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-pro")


def _parse_json_response(text: str):
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return json.loads(s)


def _premise_for_prompt(premise):
    if isinstance(premise, dict):
        return json.dumps(premise, ensure_ascii=False, indent=2)
    return str(premise)


class SlideAgent:
    @staticmethod
    def process_all(image_paths, project_dir):
        """
        For each slide: current slide image + full text of every prior slide description
        (chained accumulation, not a trivial or empty history).
        """
        _configure()
        descriptions = []
        model = genai.GenerativeModel(_flash_model())

        for i, path in enumerate(image_paths):
            prior_blocks = []
            for j in range(i):
                prior_blocks.append(f"Slide {j + 1} (full description):\n{descriptions[j]}")
            history = (
                "\n\n".join(prior_blocks)
                if prior_blocks
                else "(No prior slides yet — this is the first slide.)"
            )
            uploaded = genai.upload_file(path)
            prompt = (
                "You are describing one slide from a lecture deck.\n\n"
                "CONTEXT — full descriptions of all previous slides (verbatim, in order):\n"
                f"{history}\n\n"
                "Use that context so your description connects to what came before (themes, terms, "
                "running examples). Do not ignore prior slides.\n\n"
                "TASK: Describe ONLY the current slide image: layout, text, diagrams, and key "
                "technical or conceptual points. Be specific and non-trivial."
            )
            response = model.generate_content([prompt, uploaded])
            descriptions.append(response.text.strip())

        out = os.path.join(project_dir, "slide_description.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        return descriptions


class PremiseAgent:
    @staticmethod
    def generate(descriptions, project_dir):
        """Consumes the entire slide_description.json document (as a list). Produces structured premise.json."""
        _configure()
        model = genai.GenerativeModel(_flash_model())
        deck_json = json.dumps(
            [{"slide_index": i + 1, "description": d} for i, d in enumerate(descriptions)],
            ensure_ascii=False,
            indent=2,
        )
        prompt = f"""You are given the COMPLETE slide_description.json content for one lecture deck (all slides).

{deck_json}

Produce a STRUCTURED premise grounded in this deck: main thesis, hook, audience, and how the deck supports the argument.
Respond with JSON only, using exactly these keys:
- "thesis" (string): central claim of the lecture
- "hook" (string): one-sentence hook
- "audience" (string): who this is for
- "deck_grounding" (string): how the slide content supports the thesis (2-4 sentences)
- "premise" (string): 2-4 short paragraphs combining the above for downstream agents (plain text)
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        premise_obj = _parse_json_response(response.text)
        out = os.path.join(project_dir, "premise.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(premise_obj, f, ensure_ascii=False, indent=2)
        return premise_obj


class ArcAgent:
    @staticmethod
    def generate(premise, descriptions, project_dir):
        """Inputs: premise.json content + entire slide_description.json (all slides). Output: arc.json."""
        _configure()
        model = genai.GenerativeModel(_flash_model())
        deck_json = json.dumps(
            [{"slide_index": i + 1, "description": d} for i, d in enumerate(descriptions)],
            ensure_ascii=False,
            indent=2,
        )
        premise_block = _premise_for_prompt(premise)
        prompt = f"""Premise (from premise.json — use as authoritative grounding):
{premise_block}

Complete slide descriptions (full slide_description.json document):
{deck_json}

Produce a narrative ARC for a voiced lecture video that is consistent with the premise and progresses coherently across the whole deck.
Respond with JSON only:
- "arc" (string): full arc — opening, development in slide order, closing (plain text, specific beats)
- "slide_beats" (array of objects): one object per slide with "slide_index" (int) and "beat" (string: role in the arc)
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        arc_obj = _parse_json_response(response.text)
        out = os.path.join(project_dir, "arc.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(arc_obj, f, ensure_ascii=False, indent=2)
        return arc_obj


class NarrationAgent:
    @staticmethod
    def generate(image_paths, style, premise, arc, descriptions, project_dir):
        """
        Per slide: current image + style + premise.json + arc.json + full slide_description document
        + all prior narrations (none before slide 1). Title slide: intro + lecture overview.
        """
        _configure()
        narrations = []
        model = genai.GenerativeModel(_pro_model())

        premise_block = _premise_for_prompt(premise)
        arc_block = arc if isinstance(arc, str) else json.dumps(arc, ensure_ascii=False, indent=2)
        all_slides_doc = json.dumps(
            [{"slide_index": i + 1, "description": d} for i, d in enumerate(descriptions)],
            ensure_ascii=False,
            indent=2,
        )

        for i, path in enumerate(image_paths):
            prior_narration_lines = []
            for n in narrations:
                prior_narration_lines.append(f"Slide {n['slide_index']} narration:\n{n['narration']}")
            prior_text = (
                "\n\n".join(prior_narration_lines)
                if prior_narration_lines
                else "(No prior narrations — this is slide 1.)"
            )
            is_title = i == 0
            extra = ""
            if is_title:
                extra = (
                    "This is the TITLE slide. The speaker MUST introduce themselves by role or name "
                    "and give a clear overview of the lecture topic and what the audience will learn."
                )
            else:
                extra = (
                    "Continue naturally from the prior narrations above; do not repeat the full "
                    "introduction unless needed for a callback."
                )

            prompt = f"""Style profile (from style.json):
{json.dumps(style, ensure_ascii=False, indent=2)}

Premise (from premise.json):
{premise_block}

Arc (from arc.json):
{arc_block}

Full slide_description.json (all slides — use for cross-slide consistency):
{all_slides_doc}

Current slide index: {i + 1}. Current slide description only:
{descriptions[i]}

Prior narrations (all slides before this one — empty on slide 1):
{prior_text}

Task: Write ONLY the spoken narration script for slide {i + 1}. Match the style profile.
{extra}
Output plain speech only (no markdown headings, no slide numbers).
"""
            uploaded = genai.upload_file(path)
            response = model.generate_content([prompt, uploaded])
            narrations.append(
                {
                    "slide_index": i + 1,
                    "description": descriptions[i],
                    "narration": response.text.strip(),
                }
            )

        out = os.path.join(project_dir, "slide_description_narration.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(narrations, f, ensure_ascii=False, indent=2)
        return narrations
