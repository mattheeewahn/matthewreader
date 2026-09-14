#!/bin/bash
set -u
echo "=== Matthew Reader touch diagnostics ==="
echo
echo "[Display]"
if command -v wlr-randr >/dev/null 2>&1; then
    XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/matthew-reader}" \
    WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
    wlr-randr 2>&1 || true
else
    echo "wlr-randr not installed"
fi

echo
echo "[Touch Display 2 boot config]"
grep -nE 'vc4-kms-dsi-ili9881-7inch|swapxy|invx|invy|sizex|sizey' \
    /boot/firmware/config.txt 2>/dev/null || true

echo
echo "[Input devices]"
if command -v libinput >/dev/null 2>&1; then
    libinput list-devices 2>/dev/null | \
        grep -A18 -B2 -Ei 'touch|Goodix|GT911' || true
else
    echo "Install libinput-tools for input-device diagnostics."
fi

echo
echo "Expected v5.2 configuration:"
echo "  visual output: transform 90 clockwise"
echo "  touch overlay: swapxy + invx"
