"""Photo-decal slots for the forged-carbon wrap.

The three personal photographs are not in this repository, and their attachment
bytes were not available when the wrap was built. This module composites only
real files placed in photos/originals/. It does not generate a person, a face,
or a stand-in photograph.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from panels import REPO_ROOT, interior_rect


def _repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)

PHOTO_SPECS = (
    {
        "id": "child_giant_tire",
        "filename_stem": "child_giant_tire",
        "description": "Original photo of the child in a giant tire",
        "panel": "front_door_left",
        # After the quarter-turn, the portrait becomes a wide decal whose long side
        # runs from the window toward the sill.
        "aspect_h_over_w": 0.75,
        # Portrait photo, child centered in the tire.
        "focal": (0.50, 0.47),
        # Side panels fold outward. Clockwise puts the head toward the template center,
        # which is up on the door. Measured against the official TESLA door lettering.
        "rotation_cw": 90,
    },
    {
        "id": "child_halloween_truck",
        "filename_stem": "child_halloween_truck",
        "description": "Original photo of the child beside the purple Halloween inflatable truck",
        "panel": "hood",
        "aspect_h_over_w": 0.75,
        "focal": (0.46, 0.58),
        # The hood's image-up is the front bumper. Half a turn puts the head toward the windshield.
        "rotation_cw": 180,
    },
    {
        "id": "child_monster_truck",
        "filename_stem": "child_monster_truck",
        "description": "Original photo of the child beside the real monster truck",
        "panel": "trunk",
        "aspect_h_over_w": 0.75,
        # Child stands low in the frame, so the crop favors the lower half.
        "focal": (0.58, 0.66),
        # Image-up on the liftgate is the rear window, so the photo stays upright.
        "rotation_cw": 0,
    },
)

ACCEPTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
MIN_SHORT_SIDE = 480
MIN_LONG_SIDE = 640
LOOSE_NAME_TOKENS = ("child", "halloween", "monster", "giant_tire", "giant-tire")


class PhotoInputsBlocked(Exception):
    """Original files are missing or not usable. The wrap must stay carbon-only."""

    def __init__(self, missing: list[str], invalid: list[dict]):
        self.missing = missing
        self.invalid = invalid
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if invalid:
            parts.append("invalid " + ", ".join(item["id"] for item in invalid))
        super().__init__("photo inputs blocked: " + "; ".join(parts))


class InvalidPhoto(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def originals_dir(design_dir: Path) -> Path:
    return design_dir / "photos" / "originals"


def resolve_original(directory: Path, stem: str) -> Path | None:
    if not directory.is_dir():
        return None
    for extension in ACCEPTED_EXTENSIONS:
        candidate = directory / f"{stem}{extension}"
        if candidate.is_file():
            return candidate
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_original(path: Path) -> Image.Image:
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            rgb = image.convert("RGB")
    except Exception as exc:  # Pillow raises several decode errors.
        raise InvalidPhoto(f"not a decodable image ({exc.__class__.__name__})") from exc
    width, height = rgb.size
    short_side = min(width, height)
    long_side = max(width, height)
    if short_side < MIN_SHORT_SIDE or long_side < MIN_LONG_SIDE:
        raise InvalidPhoto(
            f"image is {width}x{height}; originals need at least "
            f"{MIN_LONG_SIDE} on the long side and {MIN_SHORT_SIDE} on the short side"
        )
    sample = np.asarray(rgb.resize((64, 64), Image.Resampling.BOX), dtype=np.float32)
    if float(sample.std()) < 8.0:
        raise InvalidPhoto("image has too little detail to be an original photograph")
    return rgb


def audit_repository(repo_root: Path, design_dir: Path) -> dict:
    """Look for the three filenames anywhere in the repo. Do not open unrelated images."""
    stems = {spec["filename_stem"] for spec in PHOTO_SPECS}
    exact = []
    loose = []
    originals = originals_dir(design_dir).resolve()
    for dirpath, dirnames, filenames in os_walk_repo(repo_root):
        dirnames[:] = [name for name in dirnames if name != ".git" and name != "__pycache__"]
        for filename in filenames:
            path = Path(dirpath) / filename
            stem = path.stem.lower()
            suffix = path.suffix.lower()
            if stem in stems and suffix in ACCEPTED_EXTENSIONS:
                exact.append(str(path.relative_to(repo_root)))
            elif any(token in stem for token in LOOSE_NAME_TOKENS) and suffix in ACCEPTED_EXTENSIONS:
                if originals in path.resolve().parents or path.resolve().parent == originals:
                    continue
                loose.append(str(path.relative_to(repo_root)))
    return {"exact_filename_matches": exact, "loose_name_matches": loose}


def os_walk_repo(root: Path):
    import os

    return os.walk(root)


def build_slots(panel_masks: dict[str, np.ndarray], solid: np.ndarray) -> list[dict]:
    slots = []
    for spec in PHOTO_SPECS:
        rect = interior_rect(panel_masks[spec["panel"]] & solid, spec["aspect_h_over_w"])
        x0, y0, x1, y1 = rect
        slots.append(
            {
                "id": spec["id"],
                "description": spec["description"],
                "panel": spec["panel"],
                "aspect_h_over_w": spec["aspect_h_over_w"],
                "rect": [int(x0), int(y0), int(x1), int(y1)],
                "focal": [float(v) for v in spec["focal"]],
                "rotation_cw": int(spec["rotation_cw"]),
            }
        )
    return slots


def rotate_clockwise(image: Image.Image, degrees: int) -> Image.Image:
    degrees = degrees % 360
    if degrees == 0:
        return image
    if degrees == 90:
        return image.transpose(Image.Transpose.ROTATE_270)
    if degrees == 180:
        return image.transpose(Image.Transpose.ROTATE_180)
    if degrees == 270:
        return image.transpose(Image.Transpose.ROTATE_90)
    raise ValueError(f"rotation must be a quarter turn, got {degrees}")


def rotate_focal(focal: tuple[float, float], degrees: int) -> tuple[float, float]:
    """Map a focal point into the image produced by rotate_clockwise."""
    x, y = float(focal[0]), float(focal[1])
    degrees = degrees % 360
    if degrees == 90:
        return (1.0 - y, x)
    if degrees == 180:
        return (1.0 - x, 1.0 - y)
    if degrees == 270:
        return (y, 1.0 - x)
    return (x, y)


def cover_crop(image: Image.Image, width: int, height: int, focal: tuple[float, float] = (0.5, 0.5)) -> np.ndarray:
    """Scale to cover the slot and keep `focal` (0..1 in the source) inside the window."""
    source_w, source_h = image.size
    scale = max(width / source_w, height / source_h)
    resized_w = max(width, int(round(source_w * scale)))
    resized_h = max(height, int(round(source_h * scale)))
    resized = image.resize((resized_w, resized_h), Image.Resampling.LANCZOS)
    left = int(round(float(focal[0]) * resized_w - width / 2))
    top = int(round(float(focal[1]) * resized_h - height / 2))
    left = min(max(left, 0), resized_w - width)
    top = min(max(top, 0), resized_h - height)
    cropped = resized.crop((left, top, left + width, top + height))
    return np.asarray(cropped, dtype=np.uint8)


def _slot_alpha(height: int, width: int) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width]
    fade = np.minimum(np.minimum(xx, width - 1 - xx), np.minimum(yy, height - 1 - yy)).astype(np.float32)
    alpha = np.clip(fade / 5.0, 0.0, 1.0)
    return alpha


def composite_photos(
    carbon_u8: np.ndarray,
    slots: list[dict],
    images: dict[str, Image.Image],
) -> np.ndarray:
    """Paste each original into its slot. `images` must already be validated."""
    painted = carbon_u8.copy()
    frame = np.array([42, 46, 50], dtype=np.float32)
    for slot in slots:
        photo = images[slot["id"]]
        x0, y0, x1, y1 = slot["rect"]
        width = x1 - x0
        height = y1 - y0
        rotation = int(slot.get("rotation_cw", 0))
        oriented = rotate_clockwise(photo, rotation)
        focal = rotate_focal(tuple(slot.get("focal", (0.5, 0.5))), rotation)
        cropped = cover_crop(oriented, width, height, focal).astype(np.float32)
        alpha = _slot_alpha(height, width)[..., None]
        base = painted[y0:y1, x0:x1].astype(np.float32)
        blended = cropped * alpha + base * (1.0 - alpha)
        fade = np.minimum(
            np.minimum(np.arange(width), width - 1 - np.arange(width))[None, :],
            np.minimum(np.arange(height), height - 1 - np.arange(height))[:, None],
        )
        border = fade < 3
        blended[border] = blended[border] * 0.45 + frame * 0.55
        painted[y0:y1, x0:x1] = np.clip(np.rint(blended), 0, 255).astype(np.uint8)
    return painted


def collect_photos(directory: Path) -> tuple[dict[str, Image.Image], dict[str, Path], list[str], list[dict]]:
    loaded: dict[str, Image.Image] = {}
    paths: dict[str, Path] = {}
    missing: list[str] = []
    invalid: list[dict] = []
    for spec in PHOTO_SPECS:
        path = resolve_original(directory, spec["filename_stem"])
        if path is None:
            missing.append(spec["id"])
            continue
        try:
            loaded[spec["id"]] = load_original(path)
            paths[spec["id"]] = path
        except InvalidPhoto as exc:
            invalid.append({"id": spec["id"], "path": str(path), "reason": exc.reason})
    return loaded, paths, missing, invalid


def photo_status(
    *,
    enable_photos: bool,
    directory: Path,
    repo_audit: dict,
    slots: list[dict],
    loaded: dict | None = None,
    paths: dict | None = None,
    missing: list[str] | None = None,
    invalid: list[dict] | None = None,
) -> dict:
    if loaded is None or paths is None or missing is None or invalid is None:
        loaded, paths, missing, invalid = collect_photos(directory)
    ready = not missing and not invalid
    if ready and enable_photos:
        state = "incorporated"
        contains = True
        reason = "The three files in photos/originals/ were composited into the decal slots."
    elif ready:
        state = "ready_but_not_applied"
        contains = False
        reason = (
            "Original files are in photos/originals/, but photo compositing was not requested, "
            "so the wrap image is still carbon only."
        )
    else:
        state = "blocked"
        contains = False
        reason = (
            "Photo incorporation is blocked. The original photograph bytes were not available: "
            "the supplied attachment paths were missing, and this repository does not contain "
            "matching files. No face, child, or scene was synthesized or substituted."
        )
    present = []
    for spec in PHOTO_SPECS:
        path = paths.get(spec["id"])
        present.append(
            {
                "id": spec["id"],
                "description": spec["description"],
                "panel": spec["panel"],
                "expected_stem": spec["filename_stem"],
                "path": _repo_relative(path) if path else None,
                "sha256": sha256_file(path) if path else None,
            }
        )
    return {
        "photo_incorporation": state,
        "wrap_contains_photos": contains,
        "reason": reason,
        "missing": missing,
        "invalid": invalid,
        "present": present,
        "repository_exact_matches": repo_audit["exact_filename_matches"],
        "repository_loose_name_matches": repo_audit["loose_name_matches"],
        "slots": slots,
        "originals_directory": _repo_relative(directory),
        "accepted_extensions": list(ACCEPTED_EXTENSIONS),
        "minimum_size": {"short_side": MIN_SHORT_SIDE, "long_side": MIN_LONG_SIDE},
    }
