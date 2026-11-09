"""Periodic dark-purple Halloween field: small bats and stars.

The field repeats on both edges, so every body panel samples the same tile.
Stars stay gold and cream, short of pure white, so they are not unfilled gaps.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

SEED = 20241031


def _star_points(cx: float, cy: float, outer: float, inner: float, points: int = 5) -> list[tuple[float, float]]:
    coords = []
    for index in range(points * 2):
        radius = outer if index % 2 == 0 else inner
        angle = -np.pi / 2 + index * np.pi / points
        coords.append((cx + radius * np.cos(angle), cy + radius * np.sin(angle)))
    return coords


def _bat_sprite(span: int) -> np.ndarray:
    """A small silhouette. Wingspan is `span` pixels."""
    span = max(12, int(span))
    width = span
    height = max(10, int(round(span * 0.58)))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = (16, 6, 24, 255)
    cx = width / 2
    cy = height * 0.62
    draw.polygon(
        [
            (cx, cy - height * 0.02),
            (width * 0.02, height * 0.28),
            (width * 0.22, height * 0.46),
            (width * 0.08, height * 0.62),
            (width * 0.30, height * 0.55),
            (width * 0.40, height * 0.78),
            (cx, cy + height * 0.02),
        ],
        fill=color,
    )
    draw.polygon(
        [
            (cx, cy - height * 0.02),
            (width * 0.98, height * 0.28),
            (width * 0.78, height * 0.46),
            (width * 0.92, height * 0.62),
            (width * 0.70, height * 0.55),
            (width * 0.60, height * 0.78),
            (cx, cy + height * 0.02),
        ],
        fill=color,
    )
    draw.ellipse(
        [cx - width * 0.09, cy - height * 0.28, cx + width * 0.09, cy + height * 0.16],
        fill=color,
    )
    draw.polygon(
        [
            (cx - width * 0.07, cy - height * 0.16),
            (cx - width * 0.02, cy - height * 0.46),
            (cx + width * 0.01, cy - height * 0.12),
        ],
        fill=color,
    )
    draw.polygon(
        [
            (cx + width * 0.07, cy - height * 0.16),
            (cx + width * 0.02, cy - height * 0.46),
            (cx - width * 0.01, cy - height * 0.12),
        ],
        fill=color,
    )
    return np.asarray(image)


def _star_sprite(size: int, color: tuple[int, int, int]) -> np.ndarray:
    size = max(5, int(size))
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outer = size * 0.48
    inner = outer * 0.42
    draw.polygon(_star_points(size / 2, size / 2, outer, inner), fill=color + (255,))
    return np.asarray(image)


def _paste_wrapped(canvas: np.ndarray, sprite: np.ndarray, cx: float, cy: float) -> None:
    height, width = canvas.shape[:2]
    sprite_h, sprite_w = sprite.shape[:2]
    y0 = int(round(cy - sprite_h / 2))
    x0 = int(round(cx - sprite_w / 2))
    ys = (np.arange(sprite_h) + y0) % height
    xs = (np.arange(sprite_w) + x0) % width
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
    if float(alpha.max()) <= 0:
        return
    current = canvas[yy, xx].astype(np.float32)
    blended = sprite[:, :, :3].astype(np.float32) * alpha + current * (1.0 - alpha)
    canvas[yy, xx] = np.clip(np.rint(blended), 0, 255).astype(np.uint8)


def render_u8(size: int = 1024, seed: int = SEED) -> np.ndarray:
    """Dark purple tile with small bats and stars. Periodic on both axes."""
    if size < 64:
        raise ValueError("size must be at least 64")
    rng = np.random.default_rng(seed)
    # Soft purple variation. A coarse lattice would need a divisor; a wrapped
    # value-noise built from the same seed keeps the base from looking flat.
    yy, xx = np.mgrid[0:size, 0:size]
    phase = rng.random(6) * 2 * np.pi
    freq = np.array([3, 5, 7, 4, 6, 2], dtype=np.float64)
    wobble = np.zeros((size, size), dtype=np.float64)
    for index, frequency in enumerate(freq):
        wobble += np.sin((xx * freq[index % 3] + yy * freq[(index + 2) % 3]) * (2 * np.pi / size) + phase[index])
    wobble = (wobble - wobble.min()) / (wobble.max() - wobble.min() + 1e-6)
    red = 36 + 22 * wobble
    green = 10 + 10 * wobble
    blue = 58 + 34 * wobble
    canvas = np.stack([red, green, blue], axis=2)
    canvas = np.clip(np.rint(canvas), 0, 255).astype(np.uint8)

    bat_cache: dict[int, np.ndarray] = {}
    for _ in range(48):
        span = int(rng.integers(16, 34))
        sprite = bat_cache.setdefault(span, _bat_sprite(span))
        angle = float(rng.uniform(-28, 28))
        turned = np.asarray(Image.fromarray(sprite).rotate(angle, expand=True, resample=Image.Resampling.BICUBIC))
        _paste_wrapped(canvas, turned, float(rng.uniform(0, size)), float(rng.uniform(0, size)))

    star_colors = ((232, 186, 72), (214, 168, 64), (236, 214, 150))
    star_cache: dict[tuple[int, tuple[int, int, int]], np.ndarray] = {}
    for _ in range(170):
        star_size = int(rng.integers(5, 13))
        color = star_colors[int(rng.integers(0, len(star_colors)))]
        sprite = star_cache.setdefault((star_size, color), _star_sprite(star_size, color))
        _paste_wrapped(canvas, sprite, float(rng.uniform(0, size)), float(rng.uniform(0, size)))
    return canvas
