"""Checks for the carbon wrap, panel coverage, and the photo-input blocker."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

DESIGN_DIR = Path(__file__).resolve().parent
if str(DESIGN_DIR) not in sys.path:
    sys.path.insert(0, str(DESIGN_DIR))

from forged_carbon import MAX_CHANNEL, render_u8
from generate_wrap import EXAMPLE_PATH, MAX_BYTES, build_wrap
from panels import REQUIRED_COVERAGE, apply_field, classify_panels, load_template, paintable_mask
from photos import PhotoInputsBlocked, collect_photos, composite_photos, load_original

REPO_ROOT = DESIGN_DIR.parents[1]


class WrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = load_template()
        cls.panels = classify_panels(cls.template)
        cls.field = render_u8(1024)
        cls.rgba = apply_field(cls.template, cls.field)

    def test_template_contract(self):
        self.assertEqual(self.template.shape, (1024, 1024, 4))

    def test_islands_partition_the_paintable_mask(self):
        paintable = paintable_mask(self.template)
        union = np.zeros(paintable.shape, dtype=bool)
        for name, mask in self.panels.items():
            if name == "trunk":
                continue
            self.assertFalse(bool((union & mask).any()), name)
            union |= mask
        self.assertTrue(np.array_equal(union, paintable))
        self.assertGreater(int(self.panels["trunk"].sum()), 15000)
        self.assertFalse(bool((self.panels["trunk"] & ~self.panels["lower_body"]).any()))

    def test_required_panels_exist(self):
        for name in REQUIRED_COVERAGE:
            self.assertGreater(int(self.panels[name].sum()), 0, name)

    def test_carbon_fills_every_paintable_pixel(self):
        rgb = self.rgba[:, :, :3]
        paintable = paintable_mask(self.template)
        near_white = (rgb[:, :, 0] >= 250) & (rgb[:, :, 1] >= 250) & (rgb[:, :, 2] >= 250)
        self.assertEqual(int((paintable & near_white).sum()), 0)
        self.assertEqual(int(near_white.sum()), 0)
        self.assertLessEqual(int(rgb.max()), MAX_CHANNEL)
        for name in REQUIRED_COVERAGE:
            self.assertEqual(int((self.panels[name] & near_white).sum()), 0, name)
            self.assertTrue(bool((self.rgba[:, :, 3][self.panels[name]] > 0).all()))

    def test_alpha_matches_template_and_outside_is_clear(self):
        self.assertTrue(np.array_equal(self.rgba[:, :, 3], self.template[:, :, 3]))
        clear = self.template[:, :, 3] == 0
        self.assertTrue(np.all(self.rgba[clear, :3] == 0))

    def test_panels_share_one_field(self):
        paintable = paintable_mask(self.template)
        self.assertTrue(np.array_equal(self.rgba[:, :, :3][paintable], self.field[paintable]))

    def test_field_is_periodic(self):
        field = self.field.astype(np.float32)
        delta_x = np.abs(np.roll(field, -1, axis=1) - field).mean(axis=2)
        delta_y = np.abs(np.roll(field, -1, axis=0) - field).mean(axis=2)
        ratios = {
            "x": float(delta_x[:, -1].mean()) / float(delta_x[:, 8:-8].mean()),
            "y": float(delta_y[-1, :].mean()) / float(delta_y[8:-8, :].mean()),
        }
        for axis, ratio in ratios.items():
            self.assertGreater(ratio, 0.7, axis)
            self.assertLess(ratio, 1.25, axis)

    def test_palette_is_dark_gunmetal(self):
        paintable = paintable_mask(self.template)
        pixels = self.rgba[:, :, :3][paintable].astype(np.float32)
        mean = pixels.mean()
        self.assertGreater(mean, 20)
        self.assertLess(mean, 90)
        spread = pixels.max(axis=1) - pixels.min(axis=1)
        self.assertLess(float(spread.mean()), 18.0)

    def test_fibers_are_not_a_single_weave_direction(self):
        gray = self.field.mean(axis=2).astype(np.float32)
        detail = gray - gaussian_filter(gray, sigma=3, mode="wrap")
        gy = np.roll(detail, -1, axis=0) - np.roll(detail, 1, axis=0)
        gx = np.roll(detail, -1, axis=1) - np.roll(detail, 1, axis=1)
        magnitude = np.hypot(gx, gy)
        angle = np.arctan2(gy, gx)
        hist, _ = np.histogram(angle, bins=12, range=(-np.pi, np.pi), weights=magnitude)
        fraction = hist / hist.sum()
        self.assertLess(float(fraction.max()), 0.18)

    def test_saved_png_meets_paint_shop_limits(self):
        self.assertLessEqual(len("Forged_Carbon.png"), 30)
        self.assertRegex("Forged_Carbon.png", r"^[A-Za-z0-9_\- ]+\.png$")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Forged_Carbon.png"
            Image.fromarray(self.rgba, "RGBA").save(path, optimize=True, compress_level=9)
            self.assertLessEqual(path.stat().st_size, MAX_BYTES)
            reloaded = np.array(Image.open(path))
            self.assertEqual(reloaded.shape, (1024, 1024, 4))

    def test_supplied_originals_are_in_the_wrap(self):
        rgba, status, _coverage = build_wrap(enable_photos=True)
        self.assertEqual(status["photo_incorporation"], "incorporated")
        self.assertTrue(status["wrap_contains_photos"])
        self.assertEqual(status["missing"], [])
        self.assertEqual(status["invalid"], [])
        stems = {Path(path).stem for path in status["repository_exact_matches"]}
        self.assertEqual(
            stems,
            {"child_giant_tire", "child_halloween_truck", "child_monster_truck"},
        )
        changed = np.any(rgba[:, :, :3] != self.rgba[:, :, :3], axis=2)
        slot_union = np.zeros(changed.shape, dtype=bool)
        for slot in status["slots"]:
            x0, y0, x1, y1 = slot["rect"]
            slot_union[y0:y1, x0:x1] = True
            self.assertTrue(bool(changed[y0 + 8 : y1 - 8, x0 + 8 : x1 - 8].all()), slot["id"])
        self.assertFalse(bool(changed[~slot_union].any()))
        self.assertTrue(EXAMPLE_PATH.is_file(), "run generate_wrap.py before the tests")
        committed = np.array(Image.open(EXAMPLE_PATH))
        self.assertTrue(np.array_equal(committed, rgba))
        self.assertLessEqual(EXAMPLE_PATH.stat().st_size, MAX_BYTES)

    def test_missing_and_partial_photos_do_not_composite(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            loaded, _paths, missing, invalid = collect_photos(directory)
            self.assertEqual(len(missing), 3)
            self.assertEqual(invalid, [])
            self.assertEqual(loaded, {})
            self._write_card(directory / "child_giant_tire.png", (900, 1200), (180, 40, 40))
            loaded, _paths, missing, invalid = collect_photos(directory)
            self.assertEqual(missing, ["child_halloween_truck", "child_monster_truck"])
            self.assertIn("child_giant_tire", loaded)
            rgba, status, _coverage = build_wrap(enable_photos=True, originals=directory)
            self.assertEqual(status["photo_incorporation"], "blocked")
            self.assertFalse(status["wrap_contains_photos"])
            self.assertTrue(np.array_equal(rgba, self.rgba))

    def test_tiny_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "child_giant_tire.png"
            Image.new("RGB", (32, 32), (10, 10, 10)).save(path)
            with self.assertRaises(Exception):
                load_original(path)

    def test_valid_originals_composite_only_inside_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            colors = {
                "child_giant_tire": (190, 30, 40),
                "child_halloween_truck": (120, 30, 180),
                "child_monster_truck": (30, 150, 60),
            }
            for stem, color in colors.items():
                self._write_card(directory / f"{stem}.png", (1000, 1400), color)
            rgba, status, _coverage = build_wrap(enable_photos=True, originals=directory)
            self.assertEqual(status["photo_incorporation"], "incorporated")
            self.assertTrue(status["wrap_contains_photos"])
            painted = rgba[:, :, :3]
            carbon = self.rgba[:, :, :3]
            changed = np.any(painted != carbon, axis=2)
            slot_union = np.zeros(changed.shape, dtype=bool)
            for slot in status["slots"]:
                x0, y0, x1, y1 = slot["rect"]
                slot_union[y0:y1, x0:x1] = True
                self.assertTrue(bool(changed[y0 + 12 : y1 - 12, x0 + 12 : x1 - 12].all()))
                self.assertTrue(bool(self.panels[slot["panel"]][y0:y1, x0:x1].all()))
            self.assertFalse(bool(changed[~slot_union].any()))
            # The front bumper has no decal. The monster-truck slot is on the trunk.
            self.assertTrue(
                np.array_equal(painted[self.panels["front_bumper"]], carbon[self.panels["front_bumper"]])
            )

    def test_decals_follow_panel_orientation(self):
        rgba, status, _coverage = build_wrap(enable_photos=True)
        slots = {slot["id"]: slot for slot in status["slots"]}
        tire = slots["child_giant_tire"]["rect"]
        door = rgba[tire[1] : tire[3], tire[0] : tire[2], :3].astype(np.float32)
        # Quarter-turn clockwise puts the sky on the center side and the grass on the outer side.
        grass = door[:, :16, 0] - door[:, :16, 2]
        sky = door[:, -16:, 0] - door[:, -16:, 2]
        self.assertGreater(float(grass.mean()), float(sky.mean()) + 15)

        hood = slots["child_halloween_truck"]["rect"]
        hood_px = rgba[hood[1] : hood[3], hood[0] : hood[2], :3].astype(np.float32)
        # Half-turn puts the bright field at the windshield edge, the bottom of this island.
        self.assertGreater(float(hood_px[-14:].mean()), float(hood_px[:14].mean()) + 20)

        trunk = slots["child_monster_truck"]["rect"]
        trunk_px = rgba[trunk[1] : trunk[3], trunk[0] : trunk[2], :3].astype(np.float32)
        self.assertGreater(float(trunk_px[:12].mean()), float(trunk_px[-12:].mean()))

    def test_compositor_refuses_to_invent_a_partial_result(self):
        slots = [
            {"id": "only", "rect": [0, 0, 10, 10]},
        ]
        with self.assertRaises(KeyError):
            composite_photos(self.field, slots, {})

    def test_photo_inputs_blocked_exception_lists_gaps(self):
        error = PhotoInputsBlocked(["child_giant_tire"], [])
        self.assertIn("child_giant_tire", error.missing)

    @staticmethod
    def _write_card(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
        width, height = size
        rng = np.random.default_rng(7)
        card = np.zeros((height, width, 3), dtype=np.uint8)
        card[:] = color
        noise = rng.integers(0, 40, size=card.shape, dtype=np.uint8)
        card = np.clip(card.astype(np.int16) + noise - 20, 0, 255).astype(np.uint8)
        Image.fromarray(card, "RGB").save(path)


if __name__ == "__main__":
    unittest.main()
