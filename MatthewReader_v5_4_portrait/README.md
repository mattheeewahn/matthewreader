# Matthew Reader v5.4 Portrait

This release keeps the Matthew Reader v1 → v5 feature set, but removes the
entire "rotate a landscape UI into portrait" approach.

## Display model

Matthew Reader now assumes the official 7-inch Touch Display 2 is used in its
native portrait coordinate system.

- No `wlr-randr --transform`
- No `rotation=90`
- No `swapxy`
- No `invx` / `invy`
- No app-side touch coordinate offset
- Raspberry Pi 5 display auto-detection enabled

The UI itself is laid out for a narrow/tall display.

## Portrait UI changes

Library:
- title/actions row
- full-width touch search row
- compact filters
- two portrait-friendly document columns
- PDF covers, Recent, Favorites and Subjects retained

Notes:
- compact portrait header
- tools arranged over multiple rows
- Pen / Highlighter / Eraser / Lasso
- Text / Auto Shape
- Line / Rectangle / Circle / Triangle / Arrow
- Undo / Redo / Delete
- P1 / P2 / P3 / H presets
- manual colors and width
- page navigation and PDF export

PDF:
- compact title/page/zoom header
- Read / Pen / Undo / TOC / Search
- Bookmark / Bookmarks / 100% / Go / Export
- P1 / P2 / P3 and 4 highlight colors
- pinch zoom, pan, annotation persistence

All v4 Settings and built-in touch keyboard features remain.

## Install

```bash
cd ~/matthewreader/MatthewReader_v5_4_portrait
sudo bash install.sh
sudo reboot
```

A reboot is required to clear old boot-time rotation settings.

## Diagnose

```bash
sudo matthew-touch-diagnostics
```

Expected:
- native portrait output, normally 720x1280
- no runtime Wayland transform
- no manual touch transform
