#!/bin/bash
set -u

echo "=== Matthew Reader v5.4 Portrait diagnostics ==="
echo
echo "[Display config]"
grep -nE 'display_auto_detect|vc4-kms-dsi-ili9881-7inch|swapxy|invx|invy|rotation=' \
    /boot/firmware/config.txt 2>/dev/null || true

echo
echo "[Command line display overrides]"
grep -oE 'video=DSI-[^ ]+|fbcon=rotate:[^ ]+' \
    /boot/firmware/cmdline.txt 2>/dev/null || echo "none"

echo
echo "[Wayland output]"
sudo -u matthew env \
    XDG_RUNTIME_DIR=/run/matthew-reader \
    WAYLAND_DISPLAY=wayland-0 \
    wlr-randr 2>&1 || true

echo
echo "[Touch input device]"
libinput list-devices 2>/dev/null | \
    grep -A20 -B3 -Ei 'touch|Goodix|GT911' || true

echo
echo "Expected v5.4 state:"
echo "  Native portrait output (normally 720x1280)"
echo "  No runtime transform"
echo "  No manual touch rotation"
