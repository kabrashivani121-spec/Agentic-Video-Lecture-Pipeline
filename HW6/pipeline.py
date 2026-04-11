import argparse
import datetime
import json
import os

from pdf2image import convert_from_path

from utils.agents import ArcAgent, NarrationAgent, PremiseAgent, SlideAgent
from utils.media import TextToSpeech, VideoAssembler
from utils.poppler_path import poppler_kwargs as _poppler_kwargs


class AgenticVideoPipeline:
    def __init__(self, pdf_path, style_path="style.json"):
        self.pdf_path = pdf_path
        self.style_path = style_path
        self.project_id = f"project_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
        self.project_dir = os.path.join("projects", self.project_id)
        self.image_dir = os.path.join(self.project_dir, "slide_images")
        self.audio_dir = os.path.join(self.project_dir, "audio")

        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)

    def run(self):
        # 1. Rasterize
        print("--- Rasterizing Slides ---")
        pp = _poppler_kwargs()
        if pp:
            print(f"Using Poppler: {pp['poppler_path']}")
        images = convert_from_path(self.pdf_path, **pp)
        image_paths = []
        for i, img in enumerate(images):
            path = os.path.join(self.image_dir, f"slide_{i + 1:03d}.png")
            img.save(path, "PNG")
            image_paths.append(path)

        # 2. Slide Description Agent
        print("--- Describing Slides ---")
        descriptions = SlideAgent.process_all(image_paths, self.project_dir)

        # 3. Premise & Arc Agents
        print("--- Building Premise & Arc ---")
        premise = PremiseAgent.generate(descriptions, self.project_dir)
        arc = ArcAgent.generate(premise, descriptions, self.project_dir)

        # 4. Narration Agent
        print("--- Generating Narrations ---")
        with open(self.style_path, "r", encoding="utf-8") as f:
            style = json.load(f)

        narrations = NarrationAgent.generate(
            image_paths, style, premise, arc, descriptions, self.project_dir
        )

        # 5. Audio Step (TTS)
        print("--- Synthesizing Audio ---")
        tts = TextToSpeech()
        audio_paths = tts.synthesize_batch(narrations, self.audio_dir)

        # 6. Video Assembly
        print("--- Assembling Final Video ---")
        output_name = os.path.splitext(os.path.basename(self.pdf_path))[0] + ".mp4"
        output_path = os.path.join(self.project_dir, output_name)
        VideoAssembler.assemble(image_paths, audio_paths, output_path)
        print(f"Done: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rasterize a PDF and build narrated video artifacts.")
    parser.add_argument(
        "--pdf",
        default="Lecture_17_AI_screenplays.pdf",
        help="Path to lecture PDF (default: Lecture_17_AI_screenplays.pdf).",
    )
    parser.add_argument(
        "--style",
        default="style.json",
        help="Path to style JSON (default: style.json).",
    )
    args = parser.parse_args()
    pipeline = AgenticVideoPipeline(args.pdf, style_path=args.style)
    pipeline.run()
