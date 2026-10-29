#!/usr/bin/env python3
"""Generate a short looping GIF of the 4×96 → 384 plate fold.

Mapping matches ``src/combine_plates.py`` (row interleave + column offset):

* Plates 1–2 → columns 1–12; plates 3–4 → columns 13–24
* Odd plates (1, 3): 96-row R → 384-row at index ``2*R`` (A→A, B→C, …)
* Even plates (2, 4): 96-row R → 384-row at index ``2*R+1`` (A→B, B→D, …)

Regenerate::

    uv run python docs/media/generate_plate_fold_gif.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from combine_plates import convert_row_interleaved  # noqa: E402

OUT = Path(__file__).with_name('four-to-384.gif')

# Autumn palette from web_app.py CSS variables
PAPER = (243, 235, 224)
PAPER2 = (255, 250, 243)
INK = (42, 33, 26)
MUTED = (111, 98, 86)
LINE = (221, 205, 186)
RUST = (154, 69, 38)
AMBER = (201, 132, 44)
OLIVE = (90, 106, 66)
COCOA = (31, 23, 18)

# Four nations (matches web --plate-1…4 / branding reference order)
PLATE_COLORS = {
    1: (79, 154, 40),    # Earth — grassy green
    2: (30, 111, 179),   # Water — deep blue
    3: (22, 164, 135),   # Air — teal/cyan
    4: (171, 22, 16),    # Fire — dark red
}

ROWS_96 = list('ABCDEFGH')
ROWS_384 = list('ABCDEFGHIJKLMNOP')
W, H = 720, 420
FPS = 12
DURATION_MS = int(1000 / FPS)


def map_well(plate: int, row: str, col: int) -> tuple[str, int]:
    """Return (new_row, new_col) using the real combiner rules."""
    new_row = convert_row_interleaved(row, plate, col)
    offset = 0 if plate in (1, 2) else 12
    return new_row, col + offset


def font(size: int) -> ImageFont.ImageFont:
    for name in (
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
        'DejaVuSans.ttf',
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = font(22)
FONT_LABEL = font(14)
FONT_SMALL = font(11)
FONT_TINY = font(9)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease(t: float) -> float:
    # smoothstep
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def plate_origin_96(plate: int) -> tuple[int, int]:
    """Top-left of each source plate in the intro layout (2×2)."""
    gap_x, gap_y = 18, 28
    pw, ph = 150, 110
    base_x, base_y = 40, 70
    col = 0 if plate in (1, 3) else 1
    row = 0 if plate in (1, 2) else 1
    return base_x + col * (pw + gap_x), base_y + row * (ph + gap_y)


def plate_384_origin() -> tuple[int, int]:
    return 300, 78


def cell_96(plate: int, row: str, col: int) -> tuple[float, float]:
    ox, oy = plate_origin_96(plate)
    cw, ch = 10.5, 10.5
    left = ox + 22
    top = oy + 18
    ri = ROWS_96.index(row)
    ci = col - 1
    return left + ci * cw + cw / 2, top + ri * ch + ch / 2


def cell_384(row: str, col: int) -> tuple[float, float]:
    ox, oy = plate_384_origin()
    cw, ch = 14.5, 16.5
    left = ox + 28
    top = oy + 22
    ri = ROWS_384.index(row)
    ci = col - 1
    return left + ci * cw + cw / 2, top + ri * ch + ch / 2


def draw_plate_96(draw: ImageDraw.ImageDraw, plate: int, fill_all: bool = True) -> None:
    ox, oy = plate_origin_96(plate)
    pw, ph = 150, 110
    color = PLATE_COLORS[plate]
    draw.rounded_rectangle(
        [ox, oy, ox + pw, oy + ph],
        radius=8,
        fill=PAPER2,
        outline=color,
        width=2,
    )
    draw.text((ox + 8, oy + 2), f'Plate {plate}', fill=color, font=FONT_SMALL)
    cw, ch = 10.5, 10.5
    left, top = ox + 22, oy + 18
    for ri, row in enumerate(ROWS_96):
        draw.text((ox + 6, top + ri * ch - 1), row, fill=MUTED, font=FONT_TINY)
        for ci in range(12):
            x0 = left + ci * cw
            y0 = top + ri * ch
            fill = (*color, ) if fill_all else PAPER
            # slight lighten empty look when not fill_all: faint dots
            if fill_all:
                draw.ellipse([x0 + 1, y0 + 1, x0 + cw - 2, y0 + ch - 2], fill=color)
            else:
                draw.ellipse(
                    [x0 + 2, y0 + 2, x0 + cw - 3, y0 + ch - 3],
                    outline=LINE,
                    width=1,
                )


def draw_plate_384_outline(draw: ImageDraw.ImageDraw, title: str = '384-well') -> None:
    ox, oy = plate_384_origin()
    pw, ph = 390, 300
    draw.rounded_rectangle(
        [ox, oy, ox + pw, oy + ph],
        radius=10,
        fill=PAPER2,
        outline=INK,
        width=2,
    )
    draw.text((ox + 10, oy + 4), title, fill=INK, font=FONT_LABEL)
    cw, ch = 14.5, 16.5
    left, top = ox + 28, oy + 22
    for ri, row in enumerate(ROWS_384):
        draw.text((ox + 8, top + ri * ch + 2), row, fill=MUTED, font=FONT_TINY)
    for ci in range(24):
        if ci in (0, 11, 12, 23):
            label = str(ci + 1)
            draw.text(
                (left + ci * cw + 2, oy + ph - 16),
                label,
                fill=MUTED,
                font=FONT_TINY,
            )


def paint_384_cell(
    draw: ImageDraw.ImageDraw,
    row: str,
    col: int,
    color: tuple[int, int, int],
    highlight: bool = False,
) -> None:
    cx, cy = cell_384(row, col)
    r = 5.5 if highlight else 4.2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    if highlight:
        draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], outline=COCOA, width=1)


def paint_96_cell(
    draw: ImageDraw.ImageDraw,
    plate: int,
    row: str,
    col: int,
    highlight: bool = False,
) -> None:
    cx, cy = cell_96(plate, row, col)
    color = PLATE_COLORS[plate]
    r = 5.0 if highlight else 3.5
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    if highlight:
        draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], outline=COCOA, width=1)


# Example wells shown moving (enough to teach the rule)
EXAMPLES = [
    (1, 'A', 1),
    (2, 'A', 1),
    (3, 'A', 1),
    (4, 'A', 1),
    (1, 'B', 1),
    (2, 'B', 1),
    (1, 'A', 12),
    (3, 'H', 12),
]


def new_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new('RGB', (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    # soft top wash
    for y in range(60):
        shade = int(247 - y * 0.15)
        draw.line([(0, y), (W, y)], fill=(shade, shade - 8, shade - 18))
    return img, draw


def draw_header(draw: ImageDraw.ImageDraw, subtitle: str) -> None:
    draw.text((24, 14), '4 × 96  →  1 × 384', fill=RUST, font=FONT_TITLE)
    draw.text((24, 42), subtitle, fill=MUTED, font=FONT_SMALL)


def draw_legend(draw: ImageDraw.ImageDraw) -> None:
    x, y = 24, H - 36
    for plate in range(1, 5):
        c = PLATE_COLORS[plate]
        draw.ellipse([x, y, x + 12, y + 12], fill=c)
        draw.text((x + 16, y - 1), f'{plate}', fill=INK, font=FONT_SMALL)
        x += 42
    draw.text((x + 8, y - 1), 'row interleave · cols 1–12 / 13–24', fill=MUTED, font=FONT_TINY)


def frame_intro(fill: bool = True) -> Image.Image:
    img, draw = new_frame()
    draw_header(draw, 'Four 96-well plates (app labels: Plate 1–4)')
    for p in range(1, 5):
        draw_plate_96(draw, p, fill_all=fill)
    draw_legend(draw)
    return img


def frame_with_examples_highlighted() -> Image.Image:
    img, draw = new_frame()
    draw_header(draw, 'Example wells will map into the 384 plate')
    for p in range(1, 5):
        draw_plate_96(draw, p, fill_all=False)
    for plate, row, col in EXAMPLES:
        paint_96_cell(draw, plate, row, col, highlight=True)
        nr, nc = map_well(plate, row, col)
        # tiny destination hint under each plate cluster is noisy; skip
        _ = (nr, nc)
    # callouts for the four A1s
    labels = [
        (1, 'A1→A1'),
        (2, 'A1→B1'),
        (3, 'A1→A13'),
        (4, 'A1→B13'),
    ]
    for plate, text in labels:
        cx, cy = cell_96(plate, 'A', 1)
        draw.text((cx + 8, cy - 10), text, fill=PLATE_COLORS[plate], font=FONT_TINY)
    draw_legend(draw)
    return img


def frame_fly(t: float) -> Image.Image:
    """t in [0,1]: wells travel from 96 coords to 384 coords."""
    img, draw = new_frame()
    draw_header(draw, 'Row interleave: odd plates → A,C,E…  even → B,D,F…')
    for p in range(1, 5):
        draw_plate_96(draw, p, fill_all=False)
    draw_plate_384_outline(draw)
    # faint empty grid dots
    for ri, row in enumerate(ROWS_384):
        for ci in range(24):
            cx, cy = cell_384(row, ci + 1)
            draw.ellipse([cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5], fill=LINE)

    et = ease(t)
    for plate, row, col in EXAMPLES:
        x0, y0 = cell_96(plate, row, col)
        nr, nc = map_well(plate, row, col)
        x1, y1 = cell_384(nr, nc)
        x, y = lerp(x0, x1, et), lerp(y0, y1, et)
        r = 5.5
        draw.ellipse([x - r, y - r, x + r, y + r], fill=PLATE_COLORS[plate])
        draw.ellipse([x - r - 1, y - r - 1, x + r + 1, y + r + 1], outline=COCOA, width=1)
    draw_legend(draw)
    return img


def frame_fill(progress: float) -> Image.Image:
    """progress 0..1: paint all 384 cells in reading order by source plate color."""
    img, draw = new_frame()
    draw_header(draw, 'Full fold: Plates 1+2 left (cols 1–12), 3+4 right (13–24)')
    for p in range(1, 5):
        draw_plate_96(draw, p, fill_all=False)
    draw_plate_384_outline(draw)

    cells: list[tuple[int, str, int, str, int]] = []
    for plate in range(1, 5):
        for row in ROWS_96:
            for col in range(1, 13):
                nr, nc = map_well(plate, row, col)
                cells.append((plate, row, col, nr, nc))
    # paint in 384 reading order for a left-to-right fill feel
    cells.sort(key=lambda c: (ROWS_384.index(c[3]), c[4]))
    n = max(1, int(len(cells) * progress))
    for plate, _or, _oc, nr, nc in cells[:n]:
        paint_384_cell(draw, nr, nc, PLATE_COLORS[plate])

    # keep example highlights on top once filled enough
    if progress > 0.15:
        for plate, row, col in EXAMPLES:
            nr, nc = map_well(plate, row, col)
            paint_384_cell(draw, nr, nc, PLATE_COLORS[plate], highlight=True)

    draw_legend(draw)
    return img


def frame_final() -> Image.Image:
    img, draw = new_frame()
    draw_header(draw, 'Result: one 16×24 plate (interleaved rows)')
    for p in range(1, 5):
        draw_plate_96(draw, p, fill_all=False)
    draw_plate_384_outline(draw, title='384-well (combined)')
    for plate in range(1, 5):
        for row in ROWS_96:
            for col in range(1, 13):
                nr, nc = map_well(plate, row, col)
                paint_384_cell(draw, nr, nc, PLATE_COLORS[plate])
    # callouts for A1 mappings
    callouts = [
        ((1, 'A', 1), 'P1 A1→A1'),
        ((2, 'A', 1), 'P2 A1→B1'),
        ((3, 'A', 1), 'P3 A1→A13'),
        ((4, 'A', 1), 'P4 A1→B13'),
    ]
    for (plate, row, col), text in callouts:
        nr, nc = map_well(plate, row, col)
        paint_384_cell(draw, nr, nc, PLATE_COLORS[plate], highlight=True)
        cx, cy = cell_384(nr, nc)
        # place labels along the top / side carefully
        if plate in (1, 2):
            draw.text((cx - 4, cy - 18), text, fill=PLATE_COLORS[plate], font=FONT_TINY)
        else:
            draw.text((cx - 20, cy - 18), text, fill=PLATE_COLORS[plate], font=FONT_TINY)
    draw_legend(draw)
    return img


def build_frames() -> list[Image.Image]:
    frames: list[Image.Image] = []
    # Intro hold ~0.9s
    intro = frame_intro(fill=True)
    frames.extend([intro] * int(0.9 * FPS))
    # Highlight examples ~0.7s
    hi = frame_with_examples_highlighted()
    frames.extend([hi] * int(0.7 * FPS))
    # Fly ~1.4s
    fly_n = int(1.4 * FPS)
    for i in range(fly_n):
        frames.append(frame_fly(i / max(1, fly_n - 1)))
    # Fill ~1.6s
    fill_n = int(1.6 * FPS)
    for i in range(fill_n):
        frames.append(frame_fill((i + 1) / fill_n))
    # Final hold ~1.4s
    final = frame_final()
    frames.extend([final] * int(1.4 * FPS))
    return frames


def verify_mapping() -> None:
    expected = {
        (1, 'A', 1): ('A', 1),
        (2, 'A', 1): ('B', 1),
        (1, 'B', 1): ('C', 1),
        (2, 'B', 1): ('D', 1),
        (3, 'A', 1): ('A', 13),
        (4, 'A', 1): ('B', 13),
        (1, 'H', 12): ('O', 12),
        (2, 'H', 12): ('P', 12),
        (3, 'H', 12): ('O', 24),
        (4, 'H', 12): ('P', 24),
    }
    for key, want in expected.items():
        got = map_well(*key)
        if got != want:
            raise AssertionError(f'mapping mismatch for {key}: {got} != {want}')


def main() -> None:
    verify_mapping()
    frames = build_frames()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=False,
    )
    seconds = len(frames) / FPS
    print(f'Wrote {OUT} ({len(frames)} frames, ~{seconds:.1f}s, {W}x{H})')


if __name__ == '__main__':
    main()
