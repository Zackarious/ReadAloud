#!/usr/bin/env python3
"""generate_badges.py - Generates consistent, high-contrast, scalable vector download badges for ReadAloud."""

import os
from pathlib import Path
import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

REPO_ROOT = Path(__file__).resolve().parent.parent
BADGES_DIR = REPO_ROOT / "data" / "badges"
BADGES_DIR.mkdir(parents=True, exist_ok=True)


def create_badge(filename: Path, icon_type: str, top_text: str, main_text: str):
    W, H = 290, 82
    surface = cairo.SVGSurface(str(filename), W, H)
    ctx = cairo.Context(surface)

    # 1. Background pill with border
    r = 16
    x, y, w, h = 1.5, 1.5, W - 3, H - 3
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -1.5707963, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, 1.5707963)
    ctx.arc(x + r, y + h - r, r, 1.5707963, 3.1415926)
    ctx.arc(x + r, y + r, r, 3.1415926, 4.7123889)
    ctx.close_path()

    # Fill background (deep rich obsidian)
    ctx.set_source_rgb(0.04, 0.05, 0.07)
    ctx.fill_preserve()

    # Stroke border
    ctx.set_source_rgba(0.30, 0.35, 0.42, 0.95)
    ctx.set_line_width(1.5)
    ctx.stroke()

    # 2. Draw Platform Icon
    if icon_type == "windows":
        # 4 Windows tiles in Microsoft Cyan/Blue
        ctx.set_source_rgb(0.0, 0.643, 0.937)
        gap = 3.5
        ts = 17
        ix, iy = 23, 23
        ctx.rectangle(ix, iy, ts, ts)
        ctx.fill()
        ctx.rectangle(ix + ts + gap, iy, ts, ts)
        ctx.fill()
        ctx.rectangle(ix, iy + ts + gap, ts, ts)
        ctx.fill()
        ctx.rectangle(ix + ts + gap, iy + ts + gap, ts, ts)
        ctx.fill()

    elif icon_type == "appimage":
        # Linux Tux Penguin
        # Head & torso
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.arc(42, 31, 9.5, 0, 6.28)
        ctx.fill()
        ctx.save()
        ctx.translate(42, 48)
        ctx.scale(1.22, 1.0)
        ctx.arc(0, 0, 11.5, 0, 6.28)
        ctx.restore()
        ctx.fill()

        # Wings
        ctx.save()
        ctx.translate(29.5, 46)
        ctx.rotate(-0.4)
        ctx.scale(0.5, 1.1)
        ctx.arc(0, 0, 8.5, 0, 6.28)
        ctx.restore()
        ctx.fill()
        ctx.save()
        ctx.translate(54.5, 46)
        ctx.rotate(0.4)
        ctx.scale(0.5, 1.1)
        ctx.arc(0, 0, 8.5, 0, 6.28)
        ctx.restore()
        ctx.fill()

        # White belly
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.save()
        ctx.translate(42, 49)
        ctx.scale(0.85, 1.0)
        ctx.arc(0, 0, 9, 0, 6.28)
        ctx.restore()
        ctx.fill()

        # White eye sockets
        ctx.save()
        ctx.translate(39.2, 29)
        ctx.scale(0.7, 1.0)
        ctx.arc(0, 0, 3.2, 0, 6.28)
        ctx.restore()
        ctx.fill()
        ctx.save()
        ctx.translate(44.8, 29)
        ctx.scale(0.7, 1.0)
        ctx.arc(0, 0, 3.2, 0, 6.28)
        ctx.restore()
        ctx.fill()

        # Black pupils
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.arc(39.8, 29.5, 1.4, 0, 6.28)
        ctx.fill()
        ctx.arc(44.2, 29.5, 1.4, 0, 6.28)
        ctx.fill()

        # Golden Beak (#f6d32d)
        ctx.set_source_rgb(0.965, 0.827, 0.176)
        ctx.move_to(36.5, 34)
        ctx.line_to(47.5, 34)
        ctx.line_to(42, 39.5)
        ctx.close_path()
        ctx.fill()

        # Golden Feet (#f6d32d)
        ctx.save()
        ctx.translate(34.5, 59)
        ctx.scale(1.25, 0.65)
        ctx.arc(0, 0, 5, 0, 6.28)
        ctx.restore()
        ctx.fill()
        ctx.save()
        ctx.translate(49.5, 59)
        ctx.scale(1.25, 0.65)
        ctx.arc(0, 0, 5, 0, 6.28)
        ctx.restore()
        ctx.fill()

    elif icon_type == "flathub":
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        # Circle
        ctx.arc(32.5, 30.5, 8, 0, 6.28)
        ctx.fill()
        # Square
        r_sq = 3
        sx, sy, sw, sh = 24.5, 43.5, 15, 15
        ctx.new_sub_path()
        ctx.arc(sx + sw - r_sq, sy + r_sq, r_sq, -1.5707963, 0)
        ctx.arc(sx + sw - r_sq, sy + sh - r_sq, r_sq, 0, 1.5707963)
        ctx.arc(sx + r_sq, sy + sh - r_sq, r_sq, 1.5707963, 3.1415926)
        ctx.arc(sx + r_sq, sy + r_sq, r_sq, 3.1415926, 4.7123889)
        ctx.close_path()
        ctx.fill()
        # Triangle
        ctx.move_to(53, 23)
        ctx.line_to(61.5, 37)
        ctx.line_to(44.5, 37)
        ctx.close_path()
        ctx.fill()
        # Plus
        ctx.rectangle(45.5, 49.5, 15, 3.8)
        ctx.fill()
        ctx.rectangle(51.1, 43.9, 3.8, 15)
        ctx.fill()

    # 3. Typography
    # Top text
    ctx.set_source_rgb(0.68, 0.72, 0.78)
    layout_top = PangoCairo.create_layout(ctx)
    layout_top.set_text(top_text, -1)
    desc_top = Pango.FontDescription("Inter, Cantarell, Segoe UI, Sans Semi-Bold 9.5")
    desc_top.set_weight(Pango.Weight.BOLD)
    layout_top.set_font_description(desc_top)

    attr_list = Pango.AttrList()
    attr_list.insert(Pango.attr_letter_spacing_new(int(1.8 * 1024)))
    layout_top.set_attributes(attr_list)

    ctx.move_to(76, 19)
    PangoCairo.show_layout(ctx, layout_top)

    # Main text
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    layout_main = PangoCairo.create_layout(ctx)
    layout_main.set_text(main_text, -1)

    font_size = 17 if "AppImage" in main_text else (18 if "Windows" in main_text else 20)
    desc_main = Pango.FontDescription(f"Inter, Cantarell, Segoe UI, Sans Bold {font_size}")
    desc_main.set_weight(Pango.Weight.BOLD)
    layout_main.set_font_description(desc_main)

    main_y = 36 if "AppImage" in main_text or "Windows" in main_text else 34
    ctx.move_to(76, main_y)
    PangoCairo.show_layout(ctx, layout_main)

    surface.finish()


def main():
    create_badge(BADGES_DIR / "download-windows.svg", "windows", "DOWNLOAD FOR", "Windows (.exe)")
    create_badge(BADGES_DIR / "download-appimage.svg", "appimage", "DOWNLOAD FOR", "Linux (.AppImage)")
    create_badge(BADGES_DIR / "download-flathub.svg", "flathub", "DOWNLOAD ON", "Flathub")
    print(f"Generated badges in {BADGES_DIR}")


if __name__ == "__main__":
    main()
