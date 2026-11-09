"""Checks for the Halloween Purple wrap and the unchanged photo slots."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
CARBON_DIR = HERE.parent / "modely-2024-forged-carbon"
sys.path.insert(0, str(CARBON_DIR))
sys.path.insert(0, str(HERE))

from generate_wrap import EXAMPLE_PATH, MAX_BYTES, build_wrap
from halloween import render_u8
from panels import load_template, paintable_mask
from photos import PHOTO_SPECS

# Frozen from the forged-carbon wrap so this design cannot drift the decals.
EXPECTED_SLOTS = {
    "child_giant_tire": {
        "panel": "front_door_left",
        "rotation_cw": 90,
        "focal": (0.50, 0.47),
        "aspect_h_over_w": 0.75,
        "rect": (42, 355, 191, 463),
    },
    "child_halloween_truck": {
        "panel": "hood",
        "rotation_cw": 180,
        "focal": (0.46, 0.58),
        "aspect_h_over_w": 0.75,
        "rect": (418, 207, 606, 344),
    },
    "child_monster_truck": {
        "panel": "trunk",
        "rotation_cw": 0,
        "focal": (0.58, 0.66),
        "aspect_h_over_w": 0.75,
        "rect": (437, 799, 588, 908),
    },
}


class HalloweenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = load_template()
        cls.field = render_u8(1024)
        cls.rgba, cls.slots, cls.incorporated, cls.missing, cls.invalid = build_wrap(enable_photos=True)

    def test_specs_match_the_carbon_wrap(self):
        self.assertEqual({spec["id"] for spec in PHOTO_SPECS}, set(EXPECTED_SLOTS))
        for spec in PHOTO_SPECS:
            expected = EXPECTED_SLOTS[spec["id"]]
            self.assertEqual(spec["panel"], expected["panel"])
            self.assertEqual(spec["rotation_cw"], expected["rotation_cw"])
            self.assertEqual(tuple(spec["focal"]), expected["focal"])
            self.assertEqual(spec["aspect_h_over_w"], expected["aspect_h_over_w"])

    def test_slots_are_unchanged(self):
        self.assertTrue(self.incorporated)
        self.assertEqual(self.missing, [])
        self.assertEqual(self.invalid, [])
        by_id = {slot["id"]: slot for slot in self.slots}
        self.assertEqual(set(by_id), set(EXPECTED_SLOTS))
        for slot_id, expected in EXPECTED_SLOTS.items():
            self.assertEqual(tuple(by_id[slot_id]["rect"]), expected["rect"])
            self.assertEqual(by_id[slot_id]["rotation_cw"], expected["rotation_cw"])
            self.assertEqual(by_id[slot_id]["panel"], expected["panel"])

    def test_paint_shop_file_limits(self):
        self.assertLessEqual(len("Halloween_Purple.png"), 30)
        self.assertEqual(self.rgba.shape, (1024, 1024, 4))
        self.assertTrue(np.array_equal(self.rgba[:, :, 3], self.template[:, :, 3]))
        self.assertTrue(EXAMPLE_PATH.is_file())
        self.assertLessEqual(EXAMPLE_PATH.stat().st_size, MAX_BYTES)
        committed = np.array(Image.open(EXAMPLE_PATH))
        self.assertTrue(np.array_equal(committed, self.rgba))

    def test_no_white_gaps_and_purple_base(self):
        paintable = paintable_mask(self.template)
        rgb = self.field
        near_white = (rgb[:, :, 0] >= 250) & (rgb[:, :, 1] >= 250) & (rgb[:, :, 2] >= 250)
        self.assertEqual(int(near_white.sum()), 0)
        # Blue-violet base: blue above green, and not a flat fill.
        self.assertGreater(float(rgb[:, :, 2].mean()), float(rgb[:, :, 1].mean()) + 25)
        self.assertGreater(float(rgb.std()), 12.0)
        slot_union = np.zeros(paintable.shape, dtype=bool)
        for slot in self.slots:
            x0, y0, x1, y1 = slot["rect"]
            slot_union[y0:y1, x0:x1] = True
        outside = paintable & ~slot_union
        self.assertTrue(np.array_equal(self.rgba[:, :, :3][outside], self.field[outside]))

    def test_field_tiles(self):
        field = self.field.astype(np.float32)
        for axis, seam, interior in (
            (1, (slice(None), -1), (slice(None), slice(8, -8))),
            (0, (-1, slice(None)), (slice(8, -8), slice(None))),
        ):
            delta = np.abs(np.roll(field, -1, axis=axis) - field).mean(axis=2)
            ratio = float(delta[seam].mean()) / float(delta[interior].mean())
            # A bat or star edge may sit on the boundary, so the mean jump can
            # exceed the interior average. A broken tile would be far larger.
            self.assertGreater(ratio, 0.4, axis)
            self.assertLess(ratio, 3.0, axis)

    def test_photos_sit_in_the_slots(self):
        purple = self.field.astype(np.float32)
        painted = self.rgba[:, :, :3].astype(np.float32)
        for slot in self.slots:
            x0, y0, x1, y1 = slot["rect"]
            self.assertGreater(float(np.abs(painted[y0:y1, x0:x1] - purple[y0:y1, x0:x1]).mean()), 15, slot["id"])


if __name__ == "__main__":
    unittest.main()
