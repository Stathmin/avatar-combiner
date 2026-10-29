#!/usr/bin/env python3
"""Rasterize the Avatar Combiner four-nations app icon into PNG / ICO exports.

Does not require Cairo; draws the same original parody mark with Pillow so lab
machines can regenerate icons with only Pillow installed.

Source vector: src/assets/app-icon.svg
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent
DOCS_ICONS = ASSETS.parents[1] / 'docs' / 'media' / 'icons'

EARTH = (79, 154, 40, 255)       # #4f9a28
WATER = (30, 111, 179, 255)      # #1e6fb3
AIR = (22, 164, 135, 255)        # #16a487
FIRE = (171, 22, 16, 255)        # #ab1610
PAPER = (243, 235, 224, 255)     # #f3ebe0
CREAM = (243, 247, 234, 255)
SKY = (234, 244, 252, 255)
MINT = (231, 255, 250, 255)
FLAME = (246, 231, 164, 255)
EDGE = (42, 33, 26, 72)


def _s(n: float, size: int) -> float:
    return n * size / 512.0


def _xy(x: float, y: float, size: int) -> tuple[float, float]:
    return _s(x, size), _s(y, size)


def _sw(size: int, design: float) -> int:
    return max(1, round(_s(design, size)))


def draw_app_icon(size: int) -> Image.Image:
    """Paint the app icon at ``size``×``size`` (RGBA)."""
    pad_r = _s(108, size)
    inset = _s(16, size)
    gap = _s(24, size)
    mid = size / 2.0
    radius_outer = _s(96, size)

    base = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(base).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=pad_r, fill=PAPER
    )

    layer = Image.new('RGBA', (size, size), PAPER)
    ld = ImageDraw.Draw(layer)
    left, top = inset, inset
    right, bottom = size - inset - 1, size - inset - 1
    gx0, gx1 = mid - gap / 2, mid + gap / 2
    gy0, gy1 = mid - gap / 2, mid + gap / 2
    ld.rectangle((left, top, gx0, gy0), fill=EARTH)
    ld.rectangle((gx1, top, right, gy0), fill=WATER)
    ld.rectangle((left, gy1, gx0, bottom), fill=AIR)
    ld.rectangle((gx1, gy1, right, bottom), fill=FIRE)

    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inset, inset, size - inset - 1, size - inset - 1),
        radius=radius_outer,
        fill=255,
    )
    clipped = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    clipped.paste(layer, (0, 0), mask)
    out = Image.alpha_composite(base, clipped)
    draw = ImageDraw.Draw(out)

    draw.rounded_rectangle(
        (inset, inset, size - inset - 1, size - inset - 1),
        radius=radius_outer,
        outline=EDGE,
        width=_sw(size, 10),
    )

    if size >= 24:
        _draw_earth(draw, size)
        _draw_water(draw, size)
        _draw_air(draw, size)
        _draw_fire(draw, size)

    return out


def _draw_earth(draw: ImageDraw.ImageDraw, size: int) -> None:
    sw = _sw(size, 18)
    pts = [_xy(86, 198, size), _xy(134, 98, size), _xy(182, 198, size)]
    draw.line(pts, fill=CREAM, width=sw, joint='curve')
    draw.line([_xy(102, 198, size), _xy(166, 198, size)], fill=CREAM, width=sw)
    if size >= 48:
        draw.line(
            [_xy(134, 142, size), _xy(134, 198, size)],
            fill=CREAM,
            width=max(1, sw - 2),
        )


def _draw_water(draw: ImageDraw.ImageDraw, size: int) -> None:
    sw = _sw(size, 16)
    cx, cy = _xy(390, 118, size)
    r = _s(52, size)
    pts = [
        (cx + r * math.cos(math.radians(deg)), cy + r * math.sin(math.radians(deg)))
        for deg in range(-50, 110, 6)
    ]
    draw.line(pts, fill=SKY, width=sw, joint='curve')
    for y in (168, 198, 228):
        x0, y0 = _xy(308, y - 28, size)
        x1, y1 = _xy(388, y + 28, size)
        draw.arc([x0, y0, x1, y1], start=200, end=340, fill=SKY, width=sw)


def _draw_air(draw: ImageDraw.ImageDraw, size: int) -> None:
    sw = _sw(size, 15)
    r = _s(36, size)
    for cx, cy in ((102, 348), (166, 348), (134, 404)):
        x, y = _xy(cx, cy, size)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=MINT, width=sw)


def _draw_fire(draw: ImageDraw.ImageDraw, size: int) -> None:
    flame = [
        _xy(378, 456, size),
        _xy(374, 404, size),
        _xy(398, 380, size),
        _xy(406, 336, size),
        _xy(430, 368, size),
        _xy(456, 392, size),
        _xy(456, 430, size),
        _xy(444, 462, size),
        _xy(406, 480, size),
        _xy(382, 468, size),
    ]
    draw.polygon(flame, fill=FLAME)
    if size >= 64:
        inner = [
            _xy(406, 456, size),
            _xy(408, 430, size),
            _xy(420, 396, size),
            _xy(442, 424, size),
            _xy(442, 444, size),
            _xy(426, 468, size),
        ]
        draw.polygon(inner, fill=(171, 22, 16, 90))


def export_all() -> list[Path]:
    DOCS_ICONS.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for size in (16, 32, 48, 64, 128, 256, 512):
        img = draw_app_icon(size)
        path = DOCS_ICONS / f'app-icon-{size}.png'
        img.save(path, format='PNG')
        written.append(path)
        if size in (256, 512):
            mirror = ASSETS / f'app-icon-{size}.png'
            img.save(mirror, format='PNG')
            written.append(mirror)

    preview = ASSETS / 'app-icon.png'
    draw_app_icon(512).save(preview, format='PNG')
    written.append(preview)

    # Pillow ICO skips sizes larger than the primary image — lead with 256.
    ico_sizes = (256, 48, 32, 16)
    ico_images = [draw_app_icon(s).convert('RGBA') for s in ico_sizes]
    ico_path = ASSETS / 'app-icon.ico'
    ico_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:],
    )
    written.append(ico_path)
    docs_ico = DOCS_ICONS / 'app-icon.ico'
    docs_ico.write_bytes(ico_path.read_bytes())
    written.append(docs_ico)

    svg_dst = DOCS_ICONS / 'app-icon.svg'
    svg_dst.write_bytes((ASSETS / 'app-icon.svg').read_bytes())
    written.append(svg_dst)

    return written


def main() -> None:
    paths = export_all()
    print('Wrote:')
    for p in paths:
        print(f'  {p}  ({p.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
