# Matthew Reader v2

Raspberry Pi kiosk e-reader/notebook designed for a 7-inch touch display.

## v2 changes
- Correct PyMuPDF import (`import pymupdf as fitz`)
- Actual Qt touch-event handling for handwriting and highlighting
- Two-finger pinch zoom (1x–4x) on PDFs
- One-finger pan while zoomed
- Swipe or edge-tap page navigation at 100%
- Automatic portrait output using `wlr-randr`
  - landscape native panel -> 90° transform
  - portrait native panel -> normal transform
- USB automatic mounting with `udiskie` on Raspberry Pi OS Lite
- Library displays USB connection status
- Built-in USB importer for PDF, `.matthew`, `.matthewscr`
- PDF `.matthewanno` sidecar is copied together when present
- Portrait-friendly compact reader toolbar

## OS
Raspberry Pi OS Lite 64-bit (Debian Trixie).

## Install / upgrade from Git
```bash
cd ~/matthewreader
git pull
sudo bash install.sh
sudo reboot
```

## Diagnostics
```bash
sudo systemctl status matthew-reader --no-pager -l
sudo journalctl -u matthew-reader -b --no-pager -n 100
cat /tmp/matthew-udiskie.log
```

To inspect Wayland output from SSH while Matthew Reader is running:
```bash
sudo -u matthew env XDG_RUNTIME_DIR=/run/matthew-reader \
  WAYLAND_DISPLAY=wayland-0 wlr-randr
```
