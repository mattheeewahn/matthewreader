#!/bin/bash
set -u

export QT_QPA_PLATFORM=wayland

# Matthew Reader v5.4 Portrait
#
# IMPORTANT:
# There is intentionally NO wlr-randr rotation here.
# The official Touch Display 2 is used in its native portrait coordinate
# system. This keeps the picture, Qt coordinates, and touchscreen coordinates
# in the same space.

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
