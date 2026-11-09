# 2024 Model Y forged carbon

Paint Shop wrap for the pre-refresh Model Y template in `modely/`. A 2024 Model Y uses that UV. The 2025 Standard, Premium, and Performance templates are different layouts and are not used here.

The finished example is `modely/example/Forged_Carbon.png`.

## What the image is

Tesla's template is a 1024×1024 visualization UV for Toybox → Paint Shop. White-looking islands in `modely/template.png` are the paintable body panels (every pixel with alpha above zero). This design fills those islands with one periodic forged-carbon field:

- chopped tow, not a woven twill
- irregular flakes of dark gunmetal gray and deep black charcoal
- fiber direction changes from flake to flake
- a clearcoat sheen for layered gloss
- the same scale and phase on the hood, roof, trunk, both doors, and the remaining islands

The field repeats across the texture edges. Hood, roof, trunk, and doors therefore sample one seamless tile, with no template white left inside the mask. The repository has no vehicle mesh and no UV weld map, so this file does not certify that every 3D panel edge lines up on the car. It is also not a print-ready vinyl template: the repo does not publish verified panel dimensions in millimeters.

Paint Shop limits followed here: PNG, 1024×1024, at most 1 MB, filename `Forged_Carbon.png`.

## Photographs in the wrap

`modely/example/Forged_Carbon.png` composites the three supplied original files. Nothing is synthesized.

| Original | Placement | Why this island |
| --- | --- | --- |
| `photos/originals/child_giant_tire.jpg` | Front door, image left | Portrait photo, child centered in the tire |
| `photos/originals/child_halloween_truck.jpg` | Roof | Landscape photo; this island keeps the child and the purple inflatable together |
| `photos/originals/child_monster_truck.jpg` | Trunk | Landscape photo; the child stays in the lower part of the frame |

Each decal is inset inside its panel, cover-cropped around that subject, and edged with a dark gunmetal frame so the carbon remains the ground. The Paint Shop UV is 1024×1024, so the decals are small on the template. `previews/photo_details.png` shows those slots enlarged. `photos/STATUS.json` records each file's sha256.

`--carbon-only` rebuilds the wrap without the decals. If an original is missing or fails validation, the generator does not fill the gap with a drawn person; it leaves the carbon in place and exits 2.

## Regenerate

```bash
python3 -m pip install -r designs/modely-2024-forged-carbon/requirements.txt
python3 designs/modely-2024-forged-carbon/generate_wrap.py
python3 designs/modely-2024-forged-carbon/test_wrap.py
```

`coverage.json` and `previews/` are rewritten by the generator. `previews/coverage.png` is green wherever the template can be painted. Red would be an unfilled white pixel.
