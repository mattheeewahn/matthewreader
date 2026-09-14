#!/bin/bash
set -u

echo "=== Matthew Reader v5.3 / Touch Display V1 ==="
echo
echo "[Native DSI mode]"
cat /sys/class/drm/card*-DSI-*/modes 2>/dev/null || true

echo
echo "[Boot config]"
grep -nE \
'display_auto_detect|vc4-kms-dsi-7inch|vc4-kms-dsi-ili9881-7inch|swapxy|invx|invy|rotation=' \
/boot/firmware/config.txt 2>/dev/null || true

echo
echo "[Wayland output]"
sudo -u matthew env \
    XDG_RUNTIME_DIR=/run/matthew-reader \
    WAYLAND_DISPLAY=wayland-0 \
    wlr-randr 2>&1 || true

echo
echo "[Touch device]"
libinput list-devices 2>/dev/null | \
    grep -A20 -B3 -Ei 'touch|FT5406|edt-ft5406' || true

echo
echo "Expected:"
echo "  native DSI mode: 800x480"
echo "  overlay: vc4-kms-dsi-7inch,swapxy,invy"
echo "  Wayland transform: 90"
echo "  Matthew orientation: 480x800 portrait"
