# Matthew Reader v5.1

v5.1 keeps all Matthew Reader v5 features and adds a Raspberry Pi touch-input compatibility fix for ordinary Qt controls under Cage/Wayland.

Touch handling:
- Buttons and menu controls: explicit touchscreen bridge
- Built-in text fields: native TouchEnd opens Matthew keyboard
- Notes/PDF canvas: unchanged native Qt touch handling
- PDF two-finger pinch/pan: unchanged

# Matthew Reader v5

v5 is built directly on v4. All v4 features remain: fullscreen kiosk boot, portrait mode, touch input, built-in QWERTY keyboard, Settings, Wi-Fi, brightness, screen timeout, USB automount/import, notebooks, PDF handwriting/highlighting, pinch zoom/pan, TOC, search, bookmarks, lasso, text, shapes, and auto-save.

## Added in v5

### PDF export
- `.matthew` / `.matthewscr` notebooks export to ordinary PDF.
- A textbook plus its `.matthewanno` sidecar exports as a new annotated PDF.
- Export can stay in `~/MatthewReader/exports` or be copied directly to a mounted USB drive.
- Originals are not overwritten.

### Automatic textbook covers
- The first PDF page is rendered into a cached cover image.
- Library cards use that cover automatically.

### Library views
- All
- Recent
- Favorites
- Textbooks
- Notes
- Scratch

Opening a document updates its Recent timestamp. Each Library card has a star button for Favorites.

### Subjects
- Assign any book or note to a subject without moving the underlying file.
- Create custom subjects such as AP Biology, US History, English, or Math.
- Filter the Library by subject.

### Enhanced shapes
- Straight line
- Rectangle
- Circle / ellipse
- Triangle
- Arrow
- Auto Shape: hand-drawn lines are straightened and closed round shapes are converted to ellipses when confidently recognized.

### Pen presets
Notebook:
- P1 black 2.0
- P2 blue 2.6
- P3 red 3.2
- H yellow highlighter

PDF:
- P1 black 2.0
- P2 blue 2.6
- P3 red 3.2

The original manual color and width controls are still present.

### Direct page jump
- PDF: tap `Go`, type a page number with Matthew's touch keyboard.
- Notebook: `Go to page` does the same.

## Upgrade

```bash
cd ~/matthewreader
git pull
sudo bash install.sh
sudo reboot
```

Existing Library files are stored outside `/opt/matthew-reader`, so reinstalling v5 does not delete normal `.matthew`, `.matthewscr`, `.matthewanno`, or textbook files.
