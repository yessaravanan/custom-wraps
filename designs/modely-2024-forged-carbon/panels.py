"""UV islands on the pre-2025 Model Y Paint Shop template.

Paintable pixels are those with alpha > 0. The template RGB is a guide; the
Camo example paints every non-transparent pixel and keeps the template alpha.
Component names come from each island's position on that template.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO_ROOT / "modely" / "template.png"

PANEL_COLORS = {
    "front_bumper": (70, 170, 220),
    "hood": (150, 80, 210),
    "trunk": (240, 180, 50),
    "front_door_left": (70, 110, 230),
    "front_door_right": (230, 120, 170),
    "rear_door_left": (40, 180, 170),
    "rear_door_right": (220, 110, 40),
    "front_fender_left": (210, 60, 60),
    "front_fender_right": (230, 180, 50),
    "rear_quarter_left": (160, 160, 255),
    "rear_quarter_right": (255, 90, 90),
    "mirror_left": (235, 235, 235),
    "mirror_right": (190, 190, 80),
    "lower_body": (70, 190, 95),
}

REQUIRED_COVERAGE = (
    "front_bumper",
    "hood",
    "trunk",
    "front_door_left",
    "front_door_right",
    "rear_door_left",
    "rear_door_right",
)


def load_template(path: Path = TEMPLATE_PATH) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    array = np.array(image)
    if array.shape != (1024, 1024, 4):
        raise ValueError(f"{path} is {array.shape}, expected 1024x1024 RGBA")
    return array


def paintable_mask(template: np.ndarray) -> np.ndarray:
    return template[:, :, 3] > 0


def classify_panels(template: np.ndarray) -> dict[str, np.ndarray]:
    """Name each connected UV island, and split the trunk out of the lower body."""
    labels, count = ndimage.label(paintable_mask(template))
    named: dict[str, np.ndarray] = {}
    for index in range(1, count + 1):
        mask = labels == index
        area = int(mask.sum())
        ys, xs = np.where(mask)
        cx = float(xs.mean())
        cy = float(ys.mean())
        name = _component_name(area, cx, cy)
        if name in named:
            raise RuntimeError(f"two islands classified as {name}")
        named[name] = mask
    if "lower_body" not in named:
        raise RuntimeError("lower body island was not found on the template")
    named["trunk"] = _trunk_mask(named["lower_body"])
    expected = set(PANEL_COLORS)
    missing = expected - set(named)
    if missing:
        raise RuntimeError(f"missing panels: {sorted(missing)}")
    return named


def _component_name(area: int, cx: float, cy: float) -> str:
    if area < 8000 and 350 < cy < 520:
        return "mirror_left" if cx < 512 else "mirror_right"
    if cx < 340 and area > 15000:
        if cy < 260:
            return "front_fender_left"
        if cy < 530:
            return "front_door_left"
        if cy < 760:
            return "rear_door_left"
        return "rear_quarter_left"
    if cx > 680 and area > 15000:
        if cy < 260:
            return "front_fender_right"
        if cy < 530:
            return "front_door_right"
        if cy < 760:
            return "rear_door_right"
        return "rear_quarter_right"
    if cy < 160 and 360 < cx < 660:
        # Short band across the nose. The large arch below it is the hood.
        return "front_bumper"
    if 180 < cy < 420 and area > 40000:
        # Hood. Its curved lower edge is the windshield, so image-down is up on the car.
        return "hood"
    if area > 80000:
        return "lower_body"
    raise RuntimeError(f"unclassified island area={area} centroid=({cx:.1f},{cy:.1f})")


def _trunk_mask(lower_body: np.ndarray) -> np.ndarray:
    """Wide center of the lower island, between the glass and the rear bumper.

    On this template the liftgate is connected to the pillars and bumper, so
    the trunk is a geometric subset rather than its own connected component.
    Rows just below the glass are thin pillars; the liftgate is the wide run
    from about y=768 to y=932.
    """
    trunk = np.zeros_like(lower_body)
    for y in range(768, 933):
        if int(lower_body[y].sum()) > 150:
            trunk[y] = lower_body[y]
    if int(trunk.sum()) < 15000:
        raise RuntimeError("trunk region is unexpectedly small")
    return trunk


def interior_rect(mask: np.ndarray, aspect_h_over_w: float, margin: int = 8) -> tuple[int, int, int, int]:
    """Axis-aligned rectangle fully inside `mask`, shaped to `aspect_h_over_w`."""
    ys, xs = np.where(mask)
    if len(xs) < 100:
        raise RuntimeError("panel is too small for a photo slot")
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    box_w = x1 - x0 + 1
    box_h = y1 - y0 + 1
    if box_h / box_w > aspect_h_over_w:
        base_w = box_w
    else:
        base_w = max(8, int(round(box_h / aspect_h_over_w)))
    cx = int(round(float(xs.mean())))
    cy = int(round(float(ys.mean())))
    height, width = mask.shape
    for scale in np.linspace(0.92, 0.30, 36):
        rect_w = max(16, int(base_w * scale))
        rect_h = max(16, int(round(rect_w * aspect_h_over_w)))
        rx0 = cx - rect_w // 2
        ry0 = cy - rect_h // 2
        rx1 = rx0 + rect_w
        ry1 = ry0 + rect_h
        if rx0 < 0 or ry0 < 0 or rx1 > width or ry1 > height:
            continue
        if not mask[ry0:ry1, rx0:rx1].all():
            continue
        inset = (
            rx0 + margin,
            ry0 + margin,
            rx1 - margin,
            ry1 - margin,
        )
        ix0, iy0, ix1, iy1 = inset
        if ix1 - ix0 >= 24 and iy1 - iy0 >= 24 and mask[iy0:iy1, ix0:ix1].all():
            return inset
    raise RuntimeError("no interior rectangle fits this panel")


def apply_field(template: np.ndarray, field_u8: np.ndarray) -> np.ndarray:
    """Paint the field into paintable pixels and keep the template alpha.

    Transparent pixels are cleared to black so leftover template white cannot
    survive in the file.
    """
    if field_u8.shape[:2] != template.shape[:2]:
        raise ValueError("field and template sizes differ")
    out = np.zeros_like(template)
    paintable = paintable_mask(template)
    out[:, :, :3] = np.where(paintable[:, :, None], field_u8, 0)
    out[:, :, 3] = template[:, :, 3]
    return out
