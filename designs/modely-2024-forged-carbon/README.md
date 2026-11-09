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

## Photos are not in the wrap

Three personal photographs were requested as decals:

1. Child in a giant tire — front door, image left
2. Child beside the purple Halloween inflatable truck — front door, image right
3. Child beside the real monster truck — trunk

Those files were not on disk. The attachment paths supplied with the request were missing, and no image in this repository matches those filenames or subjects. The generator does not draw a face, a child, a tire scene, or a truck scene. `modely/example/Forged_Carbon.png` is carbon only.

`photos/STATUS.json` records the blocker. `previews/photo_slots_blocked.png` shows where the decals would sit. The dashed boxes are only on that preview.

To add the real photographs later, put the originals in `photos/originals/` using the names in that folder's README, then run:

```bash
python3 designs/modely-2024-forged-carbon/generate_wrap.py --with-photos
```

The command exits 2 and leaves the wrap carbon-only when any original is missing, too small, or not a decodable image. A partial set is not composited.

## Regenerate

```bash
python3 -m pip install -r designs/modely-2024-forged-carbon/requirements.txt
python3 designs/modely-2024-forged-carbon/generate_wrap.py
python3 designs/modely-2024-forged-carbon/test_wrap.py
```

`coverage.json` and `previews/` are rewritten by the generator. `previews/coverage.png` is green wherever the template can be painted. Red would be an unfilled white pixel.
