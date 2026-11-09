# 2024 Model Y Halloween Purple

Paint Shop wrap for the pre-refresh Model Y template in `modely/`. The example file is `modely/example/Halloween_Purple.png`.

The ground is a dark purple tile with small bat silhouettes and gold stars. The tile repeats on both edges, and every paintable panel, including the front bumper, hood, trunk, and doors, samples it. There is no unfilled template white.

The three photographs use the same panels, crops, and rotations as the forged-carbon wrap:

| Photograph | Panel | Rotation in the file |
| --- | --- | --- |
| Child in a giant tire | Front door, image left | 90° clockwise, head toward the center |
| Child beside the purple Halloween inflatable | Hood | 180°, head toward the windshield |
| Child beside the real monster truck | Trunk | Upright, head toward the rear window |

Originals stay in `designs/modely-2024-forged-carbon/photos/originals/`. This file does not redraw them.

```bash
python3 designs/modely-2024-halloween-purple/generate_wrap.py
python3 designs/modely-2024-halloween-purple/test_wrap.py
```

`previews/halloween_preview.png` shows the wrap and a closer crop of the bats and stars. The image is a 1024×1024 Paint Shop visualization, not a certified vinyl cut file.
