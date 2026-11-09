# Original photographs

Photo decals stay out of the wrap until these three files are in this directory.
Do not add a generated, traced, or recreated picture of the child. The generator
will not invent one.

| File stem | Photograph |
| --- | --- |
| `child_giant_tire` | The child in a giant tire |
| `child_halloween_truck` | The child beside the purple Halloween inflatable truck |
| `child_monster_truck` | The child beside the real monster truck |

Accepted extensions: `.png`, `.jpg`, `.jpeg`, `.webp`.

Each file needs a long side of at least 640 pixels and a short side of at least 480 pixels.
Use the original image bytes. After the files are in place:

```bash
python3 designs/modely-2024-forged-carbon/generate_wrap.py --with-photos
```

Without `--with-photos`, a present file is reported and still left out of the PNG.
