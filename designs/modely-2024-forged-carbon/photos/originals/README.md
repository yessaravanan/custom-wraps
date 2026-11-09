# Original photographs

These three files are the photographs supplied for the wrap. The generator
pastes these bytes into the decal slots. It does not redraw the child.

| File stem | Photograph |
| --- | --- |
| `child_giant_tire` | The child in a giant tire |
| `child_halloween_truck` | The child beside the purple Halloween inflatable truck |
| `child_monster_truck` | The child beside the real monster truck |

Accepted extensions: `.png`, `.jpg`, `.jpeg`, `.webp`.

Each file needs a long side of at least 640 pixels and a short side of at least 480 pixels.
Use the original image bytes. Rebuild with:

```bash
python3 designs/modely-2024-forged-carbon/generate_wrap.py
```

`--carbon-only` leaves these files out of the PNG.
