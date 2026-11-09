"""Build the 2024 Model Y Halloween Purple Paint Shop wrap.

Photo slots, focals, and rotations are the ones already used by the forged-carbon wrap.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CARBON_DIR = HERE.parent / "modely-2024-forged-carbon"
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(CARBON_DIR))
sys.path.insert(0, str(HERE))

from halloween import render_u8
from panels import apply_field, classify_panels, load_template, paintable_mask
from photos import build_slots, collect_photos, composite_photos, originals_dir

EXAMPLE_PATH = REPO_ROOT / "modely" / "example" / "Halloween_Purple.png"
PREVIEW_PATH = HERE / "previews" / "halloween_preview.png"
MAX_BYTES = 1_000_000
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def build_wrap(enable_photos: bool = True, originals: Path | None = None):
    template = load_template()
    panels = classify_panels(template)
    solid = template[:, :, 3] >= 200
    slots = build_slots(panels, solid)
    directory = originals or originals_dir(CARBON_DIR)
    loaded, _paths, missing, invalid = collect_photos(directory)
    field = render_u8(template.shape[0])
    if enable_photos and not missing and not invalid:
        field = composite_photos(field, slots, loaded)
        incorporated = True
    else:
        incorporated = False
    rgba = apply_field(template, field)
    return rgba, slots, incorporated, missing, invalid


def _preview(rgba: np.ndarray) -> None:
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    full = Image.fromarray(rgba[:, :, :3], "RGB").resize((480, 480), Image.Resampling.LANCZOS)
    # Lower-left panels, clear of the three decals, so the bats and stars are easy to see.
    crop = Image.fromarray(rgba[680:980, 40:340, :3], "RGB").resize((420, 420), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (480 + 420 + 36, 520), (16, 8, 24))
    font = ImageFont.truetype(str(FONT_BOLD), 22) if FONT_BOLD.is_file() else ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 8), "Halloween Purple", fill=(236, 220, 160), font=font)
    draw.text((512, 8), "Bats and stars", fill=(236, 220, 160), font=font)
    canvas.paste(full, (12, 40))
    canvas.paste(crop, (504, 40))
    canvas.save(PREVIEW_PATH, optimize=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Halloween Purple Model Y wrap.")
    parser.add_argument("--carbon-only", action="store_true", help="Skip the three photographs.")
    parser.add_argument("--out", type=Path, default=EXAMPLE_PATH)
    args = parser.parse_args(argv)
    rgba, _slots, incorporated, missing, invalid = build_wrap(enable_photos=not args.carbon_only)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(args.out, format="PNG", optimize=True, compress_level=9)
    _preview(rgba)
    size = args.out.stat().st_size
    paintable = paintable_mask(load_template())
    near_white = (rgba[:, :, 0] >= 250) & (rgba[:, :, 1] >= 250) & (rgba[:, :, 2] >= 250)
    print(f"wrote {args.out} ({size} bytes) photos={incorporated} unfilled_white={int((paintable & near_white).sum())}")
    if size > MAX_BYTES:
        print(f"file exceeds {MAX_BYTES} bytes", file=sys.stderr)
        return 1
    if not args.carbon_only and not incorporated:
        print("photos missing", missing, invalid, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
