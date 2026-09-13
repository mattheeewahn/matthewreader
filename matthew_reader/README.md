# Matthew Reader

A Raspberry Pi 5 touchscreen e-reader/notebook kiosk.

## File formats
- `.matthew` — regular handwritten notebook, ZIP container
- `.matthewscr` — scratch notebook, ZIP container
- `.matthewanno` — PDF pen/highlight annotation sidecar

## Recommended OS
Raspberry Pi OS Lite (64-bit), Debian Trixie.

## Install
1. Flash Raspberry Pi OS Lite 64-bit with Raspberry Pi Imager.
2. Boot, connect network, copy this folder to the Pi.
3. Run:
   `cd matthew_reader_project`
   `sudo bash install.sh`
4. Reboot:
   `sudo reboot`

The system boots into Cage (Wayland kiosk compositor) and launches Matthew Reader fullscreen.

## Current v1 features
- Fullscreen Kindle-like library
- New `.matthew` notebook
- New `.matthewscr` scratch notebook
- Freehand pen / eraser / undo
- Multiple note pages
- PDF import
- PDF page rendering using PyMuPDF
- Tap left/right zones to change pages in Read mode
- Pen annotations on PDFs
- 4 highlight colors (yellow, green, blue, pink)
- Persistent `.matthewanno` annotations
- No desktop environment required
- systemd auto-restart if the app exits/crashes

## Notes
The official Raspberry Pi capacitive touch display does not provide active-stylus pressure or hardware palm rejection. For serious handwriting, an active-digitizer display is a hardware improvement.

Before production lockdown, keep SSH available for development. Only disable SSH after the app is stable and you have a recovery plan.
