"""Periodic non-woven forged carbon for the Model Y Paint Shop template.

The field is chopped carbon tow in resin: elongated flakes with their own
fiber direction, in dark gunmetal and deep charcoal. It is not a woven twill.
Coordinates wrap on both axes, so the texture has no cut line at the border.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

SEED = 2024
QUANTIZE_STEP = 6
# Gloss peaks stay below the near-white test so highlights never read as unfilled template.
MAX_CHANNEL = 200


def _uhash(ix: np.ndarray, iy: np.ndarray, k: int, seed: int) -> np.ndarray:
    x = (
        ix.astype(np.uint64) * np.uint64(374761393)
        + iy.astype(np.uint64) * np.uint64(668265263)
        + np.uint64(k) * np.uint64(1442695041)
        + np.uint64(seed) * np.uint64(2147483647)
    )
    x ^= x >> np.uint64(13)
    x = (x * np.uint64(1274126177)) & np.uint64(0xFFFFFFFFFFFFFFFF)
    x ^= x >> np.uint64(16)
    return (x & np.uint64(0xFFFFFFFF)).astype(np.float64) / 4294967296.0


def _cell_count(size: int, target: int) -> int:
    """Largest divisor of `size` that is at most `target`."""
    count = min(max(target, 1), size)
    while size % count != 0:
        count -= 1
    return count


def lattice_noise(size: int, cells: int, seed: int) -> np.ndarray:
    """Smooth value noise that repeats every `size` pixels."""
    n = _cell_count(size, cells)
    cell = size // n
    gy_idx, gx_idx = np.mgrid[0:n, 0:n]
    grid = _uhash(gx_idx, gy_idx, 1, seed)
    yy, xx = np.mgrid[0:size, 0:size]
    gx = xx / cell
    gy = yy / cell
    x0 = np.floor(gx).astype(np.int32) % n
    y0 = np.floor(gy).astype(np.int32) % n
    x1 = (x0 + 1) % n
    y1 = (y0 + 1) % n
    tx = gx - np.floor(gx)
    ty = gy - np.floor(gy)
    tx = tx * tx * (3.0 - 2.0 * tx)
    ty = ty * ty * (3.0 - 2.0 * ty)
    v00 = grid[y0, x0]
    v10 = grid[y0, x1]
    v01 = grid[y1, x0]
    v11 = grid[y1, x1]
    return (v00 * (1.0 - tx) + v10 * tx) * (1.0 - ty) + (v01 * (1.0 - tx) + v11 * tx) * ty


def _flakes(size: int, cell: int, points: int, seed: int, cover: float) -> dict:
    """Elliptical chopped tows. A pixel is inside a tow when its ellipse distance is < 1."""
    if size % cell != 0:
        raise ValueError(f"cell {cell} must divide size {size}")
    n = size // cell
    iy, ix = np.mgrid[0:n, 0:n]
    features = []
    for point in range(points):
        jitter_x = 0.05 + 0.90 * _uhash(ix, iy, 10 + point, seed)
        jitter_y = 0.05 + 0.90 * _uhash(ix, iy, 20 + point, seed)
        angle = _uhash(ix, iy, 30 + point, seed) * (2.0 * np.pi)
        shade = _uhash(ix, iy, 40 + point, seed)
        elongation = 2.6 + 5.2 * _uhash(ix, iy, 50 + point, seed)
        frequency = 1.35 + 1.15 * _uhash(ix, iy, 60 + point, seed)
        phase = _uhash(ix, iy, 70 + point, seed) * (2.0 * np.pi)
        width = (0.15 + 0.18 * _uhash(ix, iy, 80 + point, seed)) * cover
        depth = _uhash(ix, iy, 90 + point, seed)
        features.append(
            (jitter_x, jitter_y, angle, shade, elongation, frequency, phase, width, depth)
        )

    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    cell_x = (xx // cell).astype(np.int32)
    cell_y = (yy // cell).astype(np.int32)
    win_d = np.ones((size, size))
    win_angle = np.zeros((size, size))
    win_shade = np.zeros((size, size))
    win_frequency = np.ones((size, size))
    win_phase = np.zeros((size, size))
    win_px = np.zeros((size, size))
    win_py = np.zeros((size, size))
    win_z = np.full((size, size), -1.0)
    covered = np.zeros((size, size), dtype=bool)

    for jitter_x, jitter_y, angle, shade, elongation, frequency, phase, width, depth in features:
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        for offset_y in (-1, 0, 1):
            for offset_x in (-1, 0, 1):
                nix = (cell_x + offset_x) % n
                niy = (cell_y + offset_y) % n
                px = (cell_x + offset_x + jitter_x[niy, nix]) * cell
                py = (cell_y + offset_y + jitter_y[niy, nix]) * cell
                dx = xx - px
                dy = yy - py
                cosine = cos_a[niy, nix]
                sine = sin_a[niy, nix]
                along = dx * cosine + dy * sine
                perp = -dx * sine + dy * cosine
                half_w = np.maximum(cell * width[niy, nix], 1.0)
                half_l = half_w * elongation[niy, nix]
                distance_sq = (along / half_l) ** 2 + (perp / half_w) ** 2
                rank = depth[niy, nix]
                take = (distance_sq < 1.0) & (rank > win_z)
                win_z = np.where(take, rank, win_z)
                win_d = np.where(take, distance_sq, win_d)
                win_angle = np.where(take, angle[niy, nix], win_angle)
                win_shade = np.where(take, shade[niy, nix], win_shade)
                win_frequency = np.where(take, frequency[niy, nix], win_frequency)
                win_phase = np.where(take, phase[niy, nix], win_phase)
                win_px = np.where(take, px, win_px)
                win_py = np.where(take, py, win_py)
                covered |= take

    return {
        "d": win_d,
        "covered": covered,
        "angle": win_angle,
        "shade": win_shade,
        "frequency": win_frequency,
        "phase": win_phase,
        "px": win_px,
        "py": win_py,
        "xx": xx,
        "yy": yy,
    }


def _paint_layer(flakes: dict, marble: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    distance = np.sqrt(np.clip(flakes["d"], 0.0, 1.0))
    mask = np.clip((1.0 - distance) / 0.14, 0.0, 1.0)
    mask = np.where(flakes["covered"], mask, 0.0)
    mask = mask * mask * (3.0 - 2.0 * mask)
    cosine = np.cos(flakes["angle"])
    sine = np.sin(flakes["angle"])
    projection = (flakes["xx"] - flakes["px"]) * cosine + (flakes["yy"] - flakes["py"]) * sine
    strand = np.sin(projection * flakes["frequency"] + flakes["phase"])
    strand_fine = np.sin(projection * flakes["frequency"] * 2.1 + flakes["phase"] * 1.3)
    fiber = np.clip(0.5 + 0.5 * (0.78 * strand + 0.22 * strand_fine), 0.0, 1.0)
    fiber = np.clip((fiber - 0.35) / 0.65, 0.0, 1.0) ** 0.55
    # Marble clusters the lighter tows. Charcoal stays in the pockets; mid and light gunmetal carry the pattern.
    roll = np.clip(0.50 * flakes["shade"] + 0.50 * marble, 0.0, 1.0)
    light = roll > 0.66
    mid = (roll > 0.42) & ~light
    tone = np.where(light, 0.90 + 0.10 * flakes["shade"], np.where(mid, 0.42 + 0.16 * flakes["shade"], 0.02 + 0.08 * flakes["shade"]))
    return tone, fiber, mask


def render_field(size: int = 1024, seed: int = SEED) -> np.ndarray:
    """Return a float RGB field in 0..MAX_CHANNEL. The field is periodic."""
    if size < 64 or size % 64 != 0:
        raise ValueError("size must be a multiple of 64")
    marble = np.clip(
        0.58 * lattice_noise(size, 4, seed + 3) + 0.42 * lattice_noise(size, 8, seed + 9),
        0.0,
        1.0,
    )
    layers = (
        (_flakes(size, 64, 2, seed + 11, cover=1.22), marble, 1.0),
        (_flakes(size, 32, 2, seed + 19, cover=1.02), np.clip(0.75 * marble + 0.12, 0.0, 1.0), 0.82),
        (_flakes(size, 16, 2, seed + 29, cover=0.82), marble * 0.85, 0.42),
    )
    grain = lattice_noise(size, _cell_count(size, max(8, size // 16)), seed + 5)
    rgb = np.array([12.0, 13.0, 15.0]) + grain[..., None] * np.array([6.0, 7.0, 8.0])
    charcoal = np.array([22.0, 24.0, 26.0])
    gunmetal = np.array([176.0, 184.0, 194.0])
    for flakes, marble_layer, opacity in layers:
        tone, fiber, mask = _paint_layer(flakes, marble_layer)
        chip = charcoal + (gunmetal - charcoal) * tone[..., None]
        lift = (fiber - 0.22) * (14.0 + 36.0 * tone)
        chip = chip + lift[..., None] * np.array([0.90, 1.0, 1.12])
        alpha = (mask * opacity)[..., None]
        rgb = chip * alpha + rgb * (1.0 - alpha)

    luma = rgb.mean(axis=2)
    height = gaussian_filter(luma, sigma=0.7, mode="wrap")
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    facing = np.clip((-gx * 1.05 - gy * 0.62) / (np.hypot(gx, gy) + 3.5) + 0.08, 0.0, 1.0)
    specular = facing ** 3.2
    sharp = facing ** 14
    sheen_sigma = max(10, size // 40)
    sheen = gaussian_filter(luma, sigma=sheen_sigma, mode="wrap")
    sy = (np.roll(sheen, -1, axis=0) - np.roll(sheen, 1, axis=0)) * 0.5
    sx = (np.roll(sheen, -1, axis=1) - np.roll(sheen, 1, axis=1)) * 0.5
    broad = np.clip(0.25 + (-sx * 1.6 - sy * 0.8) / (size * 0.016), 0.0, 1.0) ** 1.1
    rgb = rgb * (0.98 + 0.16 * broad[..., None])
    highlight = np.array([0.82, 0.90, 1.0])
    rgb = rgb + (18.0 * specular + 34.0 * sharp)[..., None] * highlight
    micro = lattice_noise(size, _cell_count(size, max(16, size // 6)), seed + 77)
    rgb = rgb + (8.0 * (micro ** 2.6))[..., None] * np.array([0.82, 0.88, 1.0])
    return np.clip(rgb, 0.0, MAX_CHANNEL)


def field_to_u8(field: np.ndarray, step: int = QUANTIZE_STEP) -> np.ndarray:
    """Quantize to 8-bit. Step 6 keeps the PNG under the 1 MB Paint Shop limit."""
    values = np.clip(np.rint(field), 0, MAX_CHANNEL).astype(np.uint8)
    if step > 1:
        values = (values // np.uint8(step)) * np.uint8(step)
    return values


def render_u8(size: int = 1024, seed: int = SEED) -> np.ndarray:
    return field_to_u8(render_field(size, seed))
