#!/bin/bash
set -u

echo "=== Matthew Reader v5.3 touch diagnostics ==="
echo
echo "[Kernel]"
uname -a

echo
echo "[Touch Display 2 config]"
grep -nE 'vc4-kms-dsi-ili9881-7inch|swapxy|invx|invy|rotation=' \
    /boot/firmware/config.txt 2>/dev/null || true

echo
echo "[Kernel command line DSI overrides]"
grep -oE 'video=DSI-1:[^ ]+' /boot/firmware/cmdline.txt 2>/dev/null || echo "none"

echo
echo "[Wayland output]"
sudo -u matthew env \
    XDG_RUNTIME_DIR=/run/matthew-reader \
    WAYLAND_DISPLAY=wayland-0 \
    wlr-randr 2>&1 || true

echo
echo "[Input device]"
libinput list-devices 2>/dev/null | \
    grep -A20 -B3 -Ei 'touch|Goodix|GT911' || true

echo
echo "Expected:"
echo "  config.txt: one vc4-kms-dsi-ili9881-7inch line with rotation=90"
echo "  config.txt: no swapxy/invx/invy for this panel"
echo "  launch.sh: no wlr-randr --transform"
