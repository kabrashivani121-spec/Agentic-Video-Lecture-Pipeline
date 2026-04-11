import argparse
import json
import os

import google.generativeai as genai

from utils.agents import _flash_model, _parse_json_response


def _configure():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)


def generate_style_profile(transcript_path: str, out_path: str = "style.json") -> None:
    _configure()
    if not os.path.isfile(transcript_path):
        raise SystemExit(
            f"Transcript file not found: {transcript_path}\n"
            "Use a real file path (e.g. lecture_transcript.txt in the project folder). "
            "The README example path\\to\\transcript.txt is only a placeholder."
        )
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    prompt = f"""
    Analyze this lecture transcript and output a JSON object suitable for style.json.
    Focus on:
    - tone (e.g., academic, conversational, humorous)
    - pacing (e.g., rapid-fire, deliberate)
    - filler_usage (e.g., frequent 'um', none)
    - framing (how they introduce concepts)
    - vocabulary_level (e.g., jargon-heavy, ELI5)

    Transcript: {transcript}
    """

    model = genai.GenerativeModel(_flash_model())
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )

    data = _parse_json_response(response.text)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate style.json from a lecture transcript.")
    parser.add_argument(
        "transcript",
        nargs="?",
        default="lecture_transcript.txt",
        help="Path to plain-text transcript (default: lecture_transcript.txt).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="style.json",
        help="Output JSON path (default: style.json).",
    )
    args = parser.parse_args()
    generate_style_profile(args.transcript, args.output)
