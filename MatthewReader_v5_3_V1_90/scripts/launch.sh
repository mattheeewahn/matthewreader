#!/bin/bash
set -u

export QT_QPA_PLATFORM=wayland

# Matthew Reader v5.3 + official Raspberry Pi 7" Touch Display V1
# Native panel: 800x480 landscape
# Target Matthew orientation: 480x800 portrait
#
# V1 has no DT rotation=90 parameter, so rotate the Wayland output here.
# Touch is rotated independently at boot with swapxy,invy.

if command -v wlr-randr >/dev/null 2>&1; then
    OUT=""

    # Cage can take a moment before exposing the output.
    for _ in $(seq 1 40); do
        S="$(wlr-randr 2>/dev/null || true)"

        # Prefer a DSI output (DSI-1 on your current hardware).
        OUT="$(printf '%s\n' "$S" | awk '/^DSI-[0-9]+[[:space:]]/{print $1; exit}')"

        # Fallback to first connected output.
        if [[ -z "$OUT" ]]; then
            OUT="$(printf '%s\n' "$S" | awk '/^[^[:space:]]/{print $1; exit}')"
        fi

        [[ -n "$OUT" ]] && break
        sleep 0.1
    done

    if [[ -n "$OUT" ]]; then
        # wlroots transform 90 = 90 degrees clockwise.
        wlr-randr --output "$OUT" --transform 90 \
            >/tmp/matthew-display.log 2>&1 || true
    else
        echo "Matthew: no Wayland output found" >/tmp/matthew-display.log
    fi
fi

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
