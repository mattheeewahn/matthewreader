#!/bin/bash
set -u
export QT_QPA_PLATFORM=wayland

# Cage is already running when this script starts, so WAYLAND_DISPLAY is available.
# Force a PORTRAIT logical output automatically:
# - landscape native mode (e.g. 800x480) -> rotate 90
# - portrait native mode (e.g. 720x1280) -> normal
if command -v wlr-randr >/dev/null 2>&1; then
    sleep 0.3
    STATE="$(wlr-randr 2>/dev/null || true)"
    OUT="$(printf '%s\n' "$STATE" | awk '/^[^[:space:]].*"/ {print $1; exit}')"
    MODE="$(printf '%s\n' "$STATE" | awk '/\(.*current.*\)/ {print $1; exit}')"
    if [[ -n "${OUT:-}" && -n "${MODE:-}" ]]; then
        W="${MODE%x*}"
        H="${MODE#*x}"
        H="${H%% *}"
        if [[ "$W" =~ ^[0-9]+$ && "$H" =~ ^[0-9]+$ && "$W" -gt "$H" ]]; then
            wlr-randr --output "$OUT" --transform 90 >/dev/null 2>&1 || true
        else
            wlr-randr --output "$OUT" --transform normal >/dev/null 2>&1 || true
        fi
    fi
fi

# Raspberry Pi OS Lite has no desktop file manager to automount USB storage.
# udiskie supplies that missing removable-media automounter.
if command -v udiskie >/dev/null 2>&1; then
    udiskie --automount --no-notify --no-tray --no-file-manager --no-password-prompt >/tmp/matthew-udiskie.log 2>&1 &
fi

exec /usr/bin/python3 /opt/matthew-reader/run.py
