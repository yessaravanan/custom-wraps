"""Build the 2024 Model Y forged-carbon Paint Shop wrap and its previews.

The default output is carbon only. Photo decals are applied only with
--with-photos, and only when all three original files validate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DESIGN_DIR = Path(__file__).resolve().parent
if str(DESIGN_DIR) not in sys.path:
    sys.path.insert(0, str(DESIGN_DIR))

from forged_carbon import render_u8
from panels import (
    PANEL_COLORS,
    REPO_ROOT,
    REQUIRED_COVERAGE,
    TEMPLATE_PATH,
    apply_field,
    classify_panels,
    load_template,
    paintable_mask,
)
from photos import PHOTO_SPECS, audit_repository, build_slots, collect_photos, composite_photos, originals_dir, photo_status

EXAMPLE_PATH = REPO_ROOT / "modely" / "example" / "Forged_Carbon.png"
PREVIEW_DIR = DESIGN_DIR / "previews"
COVERAGE_PATH = DESIGN_DIR / "coverage.json"
STATUS_PATH = DESIGN_DIR / "photos" / "STATUS.json"
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
MAX_BYTES = 1_000_000


def build_wrap(enable_photos: bool = False, originals: Path | None = None) -> tuple[np.ndarray, dict, dict]:
    template = load_template()
    panels = classify_panels(template)
    solid = template[:, :, 3] >= 200
    slots = build_slots(panels, solid)
    directory = originals or originals_dir(DESIGN_DIR)
    loaded, paths, missing, invalid = collect_photos(directory)
    ready = not missing and not invalid
    field = render_u8(template.shape[0])
    incorporated = False
    if enable_photos and ready:
        field = composite_photos(field, slots, loaded)
        incorporated = True
    rgba = apply_field(template, field)
    status = photo_status(
        enable_photos=enable_photos,
        directory=directory,
        repo_audit=audit_repository(REPO_ROOT, DESIGN_DIR),
        slots=slots,
        loaded=loaded,
        paths=paths,
        missing=missing,
        invalid=invalid,
    )
    if status["wrap_contains_photos"] != incorporated:
        raise RuntimeError("photo status does not match the image that was built")
    coverage = coverage_report(template, rgba, panels, slots)
    return rgba, status, coverage


def coverage_report(
    template: np.ndarray,
    rgba: np.ndarray,
    panels: dict[str, np.ndarray],
    slots: list[dict] | None = None,
) -> dict:
    paintable = paintable_mask(template)
    rgb = rgba[:, :, :3]
    near_white = (rgb[:, :, 0] >= 250) & (rgb[:, :, 1] >= 250) & (rgb[:, :, 2] >= 250)
    photo_slots = np.zeros(paintable.shape, dtype=bool)
    for slot in slots or []:
        x0, y0, x1, y1 = slot["rect"]
        photo_slots[y0:y1, x0:x1] = True
    # Bright pixels inside a decal are part of the photograph. Unfilled means
    # template white left on the carbon itself.
    unfilled = paintable & near_white & ~photo_slots
    panel_rows = {}
    for name, mask in panels.items():
        panel_rows[name] = {
            "pixels": int(mask.sum()),
            "unfilled_white": int((mask & unfilled).sum()),
            "mean_rgb": [round(float(v), 2) for v in rgb[mask].mean(axis=0)],
        }
    return {
        "template": str(TEMPLATE_PATH.relative_to(REPO_ROOT)),
        "vehicle": "2024 Model Y (pre-2025 Paint Shop template in modely/)",
        "size": [int(template.shape[1]), int(template.shape[0])],
        "paintable_pixels": int(paintable.sum()),
        "unfilled_white_pixels": int(unfilled.sum()),
        "bright_pixels_inside_photo_slots": int((paintable & near_white & photo_slots).sum()),
        "transparent_pixels_cleared": int((rgba[:, :, 3] == 0).sum()),
        "max_channel": int(rgb.max()),
        "mean_paintable_rgb": [round(float(v), 2) for v in rgb[paintable].mean(axis=0)],
        "panels": panel_rows,
        "required_panels_fully_filled": all(
            panel_rows[name]["unfilled_white"] == 0 for name in REQUIRED_COVERAGE
        ),
        "print_ready_manufacturer_template": False,
        "notes": [
            "Paint Shop visualization UV at the template resolution (1024x1024), not a measured vinyl cut file.",
            "The repository does not publish verified body-panel dimensions in millimeters.",
            "Front bumper, hood, trunk, doors, and the other islands sample one periodic carbon field.",
        ],
    }


def save_png(path: Path, rgba: np.ndarray) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path, format="PNG", optimize=True, compress_level=9)
    return path.stat().st_size


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = FONT_BOLD_PATH if bold and FONT_BOLD_PATH.is_file() else FONT_PATH
    if path.is_file():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _legend_canvas(image: Image.Image, lines: list[tuple[str, tuple[int, int, int] | None]]) -> Image.Image:
    legend_w = 420
    canvas = Image.new("RGB", (image.width + legend_w, max(image.height, 1024)), (12, 12, 14))
    canvas.paste(image.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(18)
    title_font = _font(22, bold=True)
    x = image.width + 24
    y = 28
    for text, swatch in lines:
        if swatch is None and text.startswith("#"):
            draw.text((x, y), text[1:], fill=(236, 236, 238), font=title_font)
            y += 36
            continue
        if swatch is not None:
            draw.rectangle([x, y + 3, x + 18, y + 21], fill=swatch)
            draw.text((x + 28, y), text, fill=(220, 220, 224), font=font)
        else:
            draw.text((x, y), text, fill=(176, 176, 182), font=font)
        y += 28
    return canvas


def _dashed_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    dash, gap, width = 8, 6, 3

    def segments(start: int, end: int, horizontal: bool, fixed: int) -> None:
        cursor = start
        while cursor < end:
            stop = min(end, cursor + dash)
            if horizontal:
                draw.line([(cursor, fixed), (stop, fixed)], fill=color, width=width)
            else:
                draw.line([(fixed, cursor), (fixed, stop)], fill=color, width=width)
            cursor += dash + gap

    segments(x0, x1, True, y0)
    segments(x0, x1, True, y1)
    segments(y0, y1, False, x0)
    segments(y0, y1, False, x1)


def write_previews(
    rgba: np.ndarray,
    panels: dict[str, np.ndarray],
    slots: list[dict],
    field_u8: np.ndarray,
    photos_applied: bool,
) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    paintable = rgba[:, :, 3] > 0
    panel_rgb = np.zeros((rgba.shape[0], rgba.shape[1], 3), dtype=np.uint8)
    # Trunk is a subset of lower_body, so paint the body first and the trunk over it.
    order = ["lower_body"] + [name for name in PANEL_COLORS if name not in ("lower_body", "trunk")] + ["trunk"]
    for name in order:
        color = np.array(PANEL_COLORS[name], dtype=np.uint8)
        panel_rgb[panels[name]] = color
    lines = [("#Panel coverage", None), ("Every colored pixel is filled.", None), ("", None)]
    for name in order:
        pixels = int(panels[name].sum())
        lines.append((f"{name}  {pixels}", PANEL_COLORS[name]))
    legend = _legend_canvas(Image.fromarray(panel_rgb, "RGB"), lines)
    legend.save(PREVIEW_DIR / "panels.png", optimize=True)

    coverage = np.full((*paintable.shape, 3), 18, dtype=np.uint8)
    coverage[paintable] = (36, 150, 78)
    near_white = (rgba[:, :, 0] >= 250) & (rgba[:, :, 1] >= 250) & (rgba[:, :, 2] >= 250)
    photo_slots = np.zeros(paintable.shape, dtype=bool)
    for slot in slots:
        x0, y0, x1, y1 = slot["rect"]
        photo_slots[y0:y1, x0:x1] = True
    coverage[paintable & near_white & ~photo_slots] = (220, 48, 48)
    Image.fromarray(coverage, "RGB").save(PREVIEW_DIR / "coverage.png", optimize=True)

    crops = []
    labels = []
    for name in ("front_bumper", "hood", "front_door_left", "trunk"):
        ys, xs = np.where(panels[name])
        cx, cy = int(xs.mean()), int(ys.mean())
        half = 110
        x0 = min(max(cx - half, 0), rgba.shape[1] - 2 * half)
        y0 = min(max(cy - half, 0), rgba.shape[0] - 2 * half)
        crop = rgba[y0 : y0 + 2 * half, x0 : x0 + 2 * half, :3]
        crops.append(Image.fromarray(crop, "RGB"))
        labels.append(name)
    sheet = Image.new("RGB", (220 * len(crops), 250), (12, 12, 14))
    draw = ImageDraw.Draw(sheet)
    font = _font(18, bold=True)
    for index, (crop, label) in enumerate(zip(crops, labels)):
        sheet.paste(crop, (index * 220, 30))
        draw.text((index * 220 + 8, 4), label, fill=(230, 230, 232), font=font)
    sheet.save(PREVIEW_DIR / "crops.png", optimize=True)

    tile = 180
    corner = np.concatenate(
        [
            np.concatenate([field_u8[-tile:, -tile:], field_u8[-tile:, :tile]], axis=1),
            np.concatenate([field_u8[:tile, -tile:], field_u8[:tile, :tile]], axis=1),
        ],
        axis=0,
    )
    Image.fromarray(corner, "RGB").save(PREVIEW_DIR / "seamless.png", optimize=True)

    guide = Image.fromarray(rgba[:, :, :3], "RGB")
    draw = ImageDraw.Draw(guide)
    number_font = _font(28, bold=True)
    for index, slot in enumerate(slots, start=1):
        x0, y0, x1, y1 = slot["rect"]
        _dashed_rect(draw, (x0, y0, x1, y1), (255, 176, 48))
        draw.text((x0 + 8, y0 + 6), str(index), fill=(255, 196, 80), font=number_font)
    if photos_applied:
        slot_lines = [
            ("#Photo decals", None),
            ("These are the supplied", None),
            ("original photographs.", None),
            ("", None),
        ]
        placement_note = "IN THE WRAP"
    else:
        slot_lines = [
            ("#Photo slots blocked", None),
            ("Guides only. The wrap PNG", None),
            ("does not contain photos.", None),
            ("", None),
        ]
        placement_note = "ORIGINAL FILE REQUIRED"
    for index, slot in enumerate(slots, start=1):
        slot_lines.append((f"{index}. {slot['panel']}", (255, 176, 48)))
        for chunk in _wrap_text(slot["description"], 32):
            slot_lines.append((chunk, None))
        slot_lines.append((placement_note, None))
        slot_lines.append(("", None))
    blocked = _legend_canvas(guide, slot_lines)
    blocked.save(PREVIEW_DIR / "photo_slots.png", optimize=True)
    stale_blocked = PREVIEW_DIR / "photo_slots_blocked.png"
    if photos_applied:
        if stale_blocked.exists():
            stale_blocked.unlink()
    else:
        blocked.save(stale_blocked, optimize=True)

    details = []
    labels = []
    for slot in slots:
        x0, y0, x1, y1 = slot["rect"]
        crop = Image.fromarray(rgba[y0:y1, x0:x1, :3], "RGB")
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.NEAREST)
        details.append(crop)
        labels.append(slot["id"])
    if details:
        gap = 16
        width = sum(crop.width for crop in details) + gap * (len(details) + 1)
        height = max(crop.height for crop in details) + 48
        sheet = Image.new("RGB", (width, height), (12, 12, 14))
        draw = ImageDraw.Draw(sheet)
        font = _font(18, bold=True)
        x = gap
        for crop, label in zip(details, labels):
            sheet.paste(crop, (x, 36))
            draw.text((x, 8), label, fill=(230, 230, 232), font=font)
            x += crop.width + gap
        sheet.save(PREVIEW_DIR / "photo_details.png", optimize=True)


def _wrap_text(text: str, limit: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) > limit and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the 2024 Model Y forged-carbon wrap.")
    parser.add_argument(
        "--carbon-only",
        action="store_true",
        help="Leave the three photographs out of the wrap.",
    )
    parser.add_argument(
        "--with-photos",
        action="store_true",
        help="Composite originals from photos/originals/. This is the default.",
    )
    parser.add_argument("--out", type=Path, default=EXAMPLE_PATH)
    args = parser.parse_args(argv)
    enable_photos = not args.carbon_only

    rgba, status, coverage = build_wrap(enable_photos=enable_photos)
    size = save_png(args.out, rgba)
    coverage["output"] = str(args.out.relative_to(REPO_ROOT) if args.out.is_relative_to(REPO_ROOT) else args.out)
    coverage["file_bytes"] = size
    coverage["within_1mb"] = size <= MAX_BYTES
    coverage["photo_incorporation"] = status["photo_incorporation"]
    coverage["wrap_contains_photos"] = status["wrap_contains_photos"]

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    COVERAGE_PATH.write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")

    template = load_template()
    panels = classify_panels(template)
    # Rebuild the carbon field for the seamless preview. Photo pixels, if any, stay out of that tile.
    field = render_u8(template.shape[0])
    write_previews(rgba, panels, status["slots"], field, photos_applied=status["wrap_contains_photos"])

    print(f"wrote {args.out} ({size} bytes)")
    print(f"photo_incorporation={status['photo_incorporation']} contains_photos={status['wrap_contains_photos']}")
    print(f"unfilled_white={coverage['unfilled_white_pixels']} max_channel={coverage['max_channel']}")
    if size > MAX_BYTES:
        print(f"file exceeds {MAX_BYTES} bytes", file=sys.stderr)
        return 1
    if enable_photos and not status["wrap_contains_photos"]:
        print(status["reason"], file=sys.stderr)
        for item in status["missing"]:
            print(f"missing: {item}", file=sys.stderr)
        for item in status["invalid"]:
            print(f"invalid: {item['id']}: {item['reason']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
