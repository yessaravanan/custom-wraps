# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A content-only repository (no code, build, lint, or tests) of Tesla custom-wrap templates and example wraps for the in-car Paint Shop. Everything is PNG images plus Markdown. The root `README.md` doubles as the public user guide (upload steps, image requirements, USB setup), so edits to requirements go there.

## Layout

Each vehicle variant is a top-level directory (`cybertruck/`, `model3/`, `model3-2024-base/`, `model3-2024-performance/`, `modely/`, `modely-2025-*`, `modely-l/`, `models-2021/`, `models-2025-plaid/`, `modelx-2021/`) with the same structure:

- `template.png`: the UV-layout template users paint over. 1024x1024 for every model except Cybertruck (1024x768).
- `vehicle_image.png`: thumbnail shown in the root README's vehicle table.
- `example/*.png`: sample wraps (about 20 per model, 36 for Cybertruck).
- `README.md`: shows the template and an `<img>` thumbnail for every file in `example/`. The per-model READMEs are near-identical copies that differ only in title and the example list.

`images/` holds the two Paint Shop screenshots used by the root README.

## Keeping things in sync

Adding a new vehicle variant means creating the directory with all four items above and adding a cell to the `<table>` in the root `README.md` (three cells per row). Adding or removing an example PNG means updating that model's `README.md` example list by hand, since nothing generates it; keep entries alphabetical like the existing ones.

Example wraps and templates must satisfy the repo's own stated constraints: PNG, 512x512 to 1024x1024, 1 MB max, filenames of alphanumerics, underscores, dashes and spaces only, at most 30 characters.

The per-model READMEs link back to `https://github.com/teslamotors/custom-wraps`; leave those URLs as they are.
