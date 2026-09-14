#!/bin/bash
set -u

export QT_QPA_PLATFORM=wayland

# v5.3: no wlr-randr transform here.
# The official Touch Display 2 is rotated in the kernel using:
#   dtoverlay=vc4-kms-dsi-ili9881-7inch,rotation=90
# This keeps visual output and touch coordinates in one coordinate system.

if command -v udiskie >/dev/null 2>&1; then
    udiskie \
        --automount \
        --no-notify \
        --no-tray \
        --no-file-manager \
        --no-password-prompt \
        >/tmp/matthew-udiskie.log 2>&1 &
fi

exec /usr/bin/python3 /opt/matthew-reader/run.py
