#!/usr/bin/env python3
"""Render README stories from real learning-loop or four-month demo state.

This is a contributor-only helper. DeutschDNA itself remains dependency-free;
rendering the GIF requires Pillow.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as exc:  # pragma: no cover - contributor guidance
    raise SystemExit("Pillow is required to render the GIF: python -m pip install pillow") from exc

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import demo  # noqa: E402
import deutsch_dna as dna  # noqa: E402


WIDTH = 1180
HEIGHT = 760
FRAME_DURATIONS_MS = [3000, 3400, 3000, 5000]
LEARNING_DURATIONS_MS = [3200, 4300, 5000, 6500]

COLORS = {
    "page": "#11111b",
    "terminal": "#181825",
    "border": "#45475a",
    "text": "#cdd6f4",
    "muted": "#7f849c",
    "accent": "#d9ff45",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "red": "#f38ba8",
    "lavender": "#cba6f7",
}

FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/CascadiaMono.ttf"),
    Path("C:/Windows/Fonts/consola.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
    Path("/System/Library/Fonts/SFNSMono.ttf"),
)

SYMBOL_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/seguisym.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Apple Symbols.ttf"),
)

SYMBOLS = frozenset("▱▰↺←→✓✗★")


def find_font(explicit: str | None) -> Path:
    candidates = (Path(explicit).expanduser(),) if explicit else FONT_CANDIDATES
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit("No monospaced font found. Pass one with --font PATH.")


def find_symbol_font() -> Path:
    for candidate in SYMBOL_FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit("No symbol font found for the CLI's progress and timeline glyphs.")


def capture_cli(home: Path, arguments: tuple[str, ...]) -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = dna.main(["--home", str(home), *arguments])
    if code:
        raise RuntimeError(f"Demo command failed with exit code {code}: {' '.join(arguments)}")
    return stream.getvalue().strip()


def collect_screens() -> list[tuple[str, str, str]]:
    with tempfile.TemporaryDirectory(prefix="deutschdna-gif-") as directory:
        home = Path(directory)
        demo.seed(home)
        warten_id = dna.mistake_id("preposition", "warten auf + accusative")
        warten = dna.StateStore(home).show(warten_id)
        wrong_moments = sorted(dna.parse_moment(example["seen_at"]) for example in warten["examples"])
        comeback_days = (wrong_moments[-1] - wrong_moments[-2]).days
        screens = (
            ("01  REMEMBERS YOU", ("recap", "--format", "card")),
            ("02  FINDS THE ROOT CAUSE", ("summary", "--format", "text")),
            (
                "03  SHOWS THE JOURNEY",
                ("show", dna.mistake_id("case", "mit + dative"), "--format", "text"),
            ),
            (
                f"04  {comeback_days} DAYS LATER · IT REMEMBERS",
                ("show", warten_id, "--format", "text"),
            ),
        )
        return [
            (label, f"$ python scripts/deutsch_dna.py {' '.join(arguments)}", capture_cli(home, arguments))
            for label, arguments in screens
        ]


def collect_learning_screens() -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="deutschdna-learning-gif-") as directory:
        home = Path(directory)
        demo.seed_learning_loop(home)
        mistake = dna.StateStore(home).show(dna.mistake_id("case", "mit + dative"))
        proof = dna.learning_proof_view(mistake["learning_proof"])
        if not proof or proof["independent"]["source"] != "spontaneous":
            raise RuntimeError("The demo must produce real transfer evidence before it can be rendered")
        support, independent = proof["with_help"], proof["independent"]
        practice = next(entry for entry in mistake["coaching_history"] if entry["outcome"] == "independent")
        label = dna.display_label(mistake)[0]
        return [
            {
                "stage": "01 / FIRST SESSION", "title": "Your words become the lesson.",
                "description": "One small mistake gives your tutor something specific to remember.",
                "rows": [("YOU WROTE", mistake["first_example"]["original"], "red"),
                         ("THE PATTERN IT REMEMBERS", label, "text")],
                "footer": "Your own sentence is the starting point.",
            },
            {
                "stage": "02 / A SMALL HINT", "title": "You find the correction.",
                "description": "Your tutor saves the help you used and the answer you produced.",
                "rows": [("YOUR TUTOR", support["hint"], "blue"),
                         ("YOU REPAIRED IT", support["answer"], "green")],
                "footer": f"Remembered approach: {support['strategy']}",
            },
            {
                "stage": "03 / A NEW SITUATION", "title": "Now try a different sentence.",
                "description": "A fresh task gives you room to use the same structure yourself.",
                "rows": [("YOUR NEXT TASK", practice["prompt"], "blue"),
                         ("YOUR ANSWER, WITHOUT A HINT", practice["answer"], "green")],
                "footer": "Correct in a new situation, without help.",
            },
            {
                "stage": "04 / THE NEXT DAY", "title": "Then it notices your progress.",
                "description": "Your tutor remembers the hint you needed the day before.",
                "rows": [(f"{support['at_local'][:10]} / WITH A HINT", support["answer"], "text"),
                         (f"{independent['at_local'][:10]} / UNPROMPTED", independent["answer"], "green")],
                "footer": f"This time, you used {label} without help.",
            },
        ]


def wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.getlength(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) == 2:
        words = text.split()
        candidates = [(" ".join(words[:index]), " ".join(words[index:])) for index in range(1, len(words))]
        candidates = [pair for pair in candidates if all(font.getlength(line) <= width for line in pair)]
        if candidates:
            sentence_breaks = [pair for pair in candidates if pair[0].endswith((".", "?", "!", ":"))]
            candidates = sentence_breaks or candidates
            lines = list(min(candidates, key=lambda pair: abs(font.getlength(pair[0]) - font.getlength(pair[1]))))
    if any(font.getlength(line) > width for line in lines):
        raise ValueError("Story text exceeds its panel width")
    return lines


def render_learning_frame(screen: dict, index: int, count: int, font_path: Path) -> Image.Image:
    heading = ImageFont.truetype(str(font_path), 40)
    quote = ImageFont.truetype(str(font_path), 32)
    body = ImageFont.truetype(str(font_path), 22)
    small = ImageFont.truetype(str(font_path), 19)
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["page"])
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, WIDTH - 24, HEIGHT - 24), radius=22, fill=COLORS["terminal"])
    draw.text((52, 44), "DeutschDNA", font=body, fill=COLORS["accent"])
    badge = "SCRIPTED LEARNER / REAL ENGINE"
    draw.text((WIDTH - 52 - small.getlength(badge), 47), badge, font=small, fill=COLORS["muted"])
    draw.text((52, 96), screen["stage"], font=small, fill=COLORS["accent"])
    if heading.getlength(screen["title"]) > WIDTH - 104:
        raise ValueError("Story title exceeds its available width")
    draw.text((50, 129), screen["title"], font=heading, fill=COLORS["text"])
    draw.text((52, 190), screen["description"], font=body, fill=COLORS["text"])

    for row_index, (label, text, color) in enumerate(screen["rows"]):
        top = 245 + row_index * 187
        draw.rounded_rectangle((50, top, WIDTH - 50, top + 166), radius=14,
                               fill=COLORS["page"], outline=COLORS["border"], width=1)
        draw.text((76, top + 19), label, font=small, fill=COLORS["muted"])
        lines = wrap_text(text, quote, WIDTH - 152)
        if len(lines) > 2:
            raise ValueError("Story quote exceeds its two-line panel")
        for line_index, line in enumerate(lines):
            draw.text((76, top + 56 + line_index * 40), line, font=quote, fill=COLORS[color])

    draw.text((52, 635), screen["footer"], font=body, fill=COLORS["accent"])
    track_width = (WIDTH - 104 - 30) // count
    for stage in range(count):
        left = 52 + stage * (track_width + 10)
        color = COLORS["accent"] if stage <= index else COLORS["border"]
        draw.rounded_rectangle((left, 698, left + track_width, 702), radius=2, fill=color)
    return image


def ellipsize(text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    if font.getlength(text) <= width:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = f"{text[:middle]}…"
        if font.getlength(candidate) <= width:
            low = middle
        else:
            high = middle - 1
    return f"{text[:low]}…"


def color_for_line(line: str) -> str:
    if line.startswith("DeutschDNA"):
        return COLORS["accent"]
    if line.startswith("Ursache:") or line.startswith("  →"):
        return COLORS["lavender"]
    if "✗" in line or "← schwach" in line:
        return COLORS["red"]
    if "✓" in line:
        return COLORS["green"]
    if "★" in line:
        return COLORS["yellow"]
    if line.startswith("Jetzt fällig:"):
        return COLORS["peach"]
    if line.startswith("Regel:"):
        return COLORS["blue"]
    return COLORS["text"]


def draw_monospace_line(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    body_font: ImageFont.FreeTypeFont,
    symbol_font: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
) -> None:
    x, y = position
    cell_width = body_font.getlength("M")
    max_characters = max(1, int(max_width // cell_width))
    visible = text if len(text) <= max_characters else f"{text[: max_characters - 1]}…"
    for index, character in enumerate(visible):
        font = symbol_font if character in SYMBOLS else body_font
        character_width = font.getlength(character)
        character_x = x + index * cell_width + max(0, (cell_width - character_width) / 2)
        draw.text((character_x, y), character, font=font, fill=fill)


def render_frame(
    screen: tuple[str, str, str],
    index: int,
    count: int,
    fonts: tuple[ImageFont.FreeTypeFont, ...],
) -> Image.Image:
    label_font, prompt_font, body_font, small_font, symbol_font = fonts
    label, command, output = screen
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["page"])
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (26, 26, WIDTH - 26, HEIGHT - 26),
        radius=22,
        fill=COLORS["terminal"],
        outline=COLORS["border"],
        width=2,
    )
    for offset, color in enumerate((COLORS["red"], COLORS["yellow"], COLORS["green"])):
        left = 50 + offset * 23
        draw.ellipse((left, 49, left + 12, 61), fill=color)

    draw.text((50, 82), label, font=label_font, fill=COLORS["accent"])
    badge = "REAL ENGINE  ·  120 DAYS  ·  LOCAL JSON"
    badge_width = small_font.getlength(badge)
    draw.text((WIDTH - 52 - badge_width, 88), badge, font=small_font, fill=COLORS["muted"])

    draw.text((50, 124), ellipsize(command, prompt_font, WIDTH - 100), font=prompt_font, fill=COLORS["blue"])
    draw.line((50, 154, WIDTH - 50, 154), fill=COLORS["border"], width=1)

    y = 176
    line_height = 23
    for line in output.splitlines():
        if y + line_height > 686:
            draw.text((50, y), "…", font=body_font, fill=COLORS["muted"])
            break
        draw_monospace_line(
            draw,
            (50, y),
            line,
            body_font,
            symbol_font,
            color_for_line(line),
            WIDTH - 100,
        )
        y += line_height

    draw.line((50, 700, WIDTH - 50, 700), fill=COLORS["border"], width=1)
    draw.text((50, 714), "Generated from scripts/demo.py — no hard-coded scores", font=small_font, fill=COLORS["muted"])
    for dot in range(count):
        color = COLORS["accent"] if dot == index else COLORS["border"]
        left = WIDTH - 50 - ((count - dot) * 18)
        draw.ellipse((left, 716, left + 8, 724), fill=color)

    return image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render demo/deutschdna.gif from the real demo engine")
    parser.add_argument("--story", choices=("history", "learning-loop"), default="history")
    parser.add_argument("--output", help="Output GIF path; defaults to demo/deutschdna.gif or demo/learning-loop.gif")
    parser.add_argument("--font", help="Path to a monospaced TrueType font")
    parser.add_argument("--frames-dir", help="Also save PNG frames for visual inspection")
    arguments = parser.parse_args(argv)

    font_path = find_font(arguments.font)
    symbol_font_path = find_symbol_font()
    fonts = (
        ImageFont.truetype(str(font_path), 22),
        ImageFont.truetype(str(font_path), 16),
        ImageFont.truetype(str(font_path), 16),
        ImageFont.truetype(str(font_path), 13),
        ImageFont.truetype(str(symbol_font_path), 17),
    )
    if arguments.story == "learning-loop":
        screens = collect_learning_screens()
        frames = [render_learning_frame(screen, index, len(screens), font_path) for index, screen in enumerate(screens)]
        durations = LEARNING_DURATIONS_MS
        default_output = "demo/learning-loop.gif"
    else:
        screens = collect_screens()
        frames = [render_frame(screen, index, len(screens), fonts) for index, screen in enumerate(screens)]
        durations = FRAME_DURATIONS_MS
        default_output = "demo/deutschdna.gif"

    output = Path(arguments.output or default_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    if arguments.story == "learning-loop":
        frames[-1].save(output.with_suffix(".png"))
    if arguments.frames_dir:
        frames_dir = Path(arguments.frames_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(frames, 1):
            frame.save(frames_dir / f"frame-{index}.png")
    print(f"Rendered {len(frames)} real-engine screens to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
