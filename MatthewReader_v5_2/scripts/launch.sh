#!/bin/bash
set -u

export QT_QPA_PLATFORM=wayland

# Matthew Reader v5.2:
# The official 7" Touch Display 2 is natively portrait (720x1280).
# Matthew is intentionally locked 90 degrees clockwise (landscape).
#
# Touch coordinates are rotated independently at boot by
# configure-touch-display.sh using the Touch Display 2 DT overlay:
#   swapxy,invx
#
# Do NOT make this rotation automatic based on width/height; doing so can
# leave the visual output and touchscreen in different coordinate systems.
if command -v wlr-randr >/dev/null 2>&1; then
    OUT=""
    for _ in $(seq 1 30); do
        S="$(wlr-randr 2>/dev/null || true)"

        # Prefer a DSI panel. Fall back to the first connected output.
        OUT="$(printf '%s\n' "$S" | awk '/^DSI-[0-9]+[[:space:]]/{print $1; exit}')"
        if [[ -z "$OUT" ]]; then
            OUT="$(printf '%s\n' "$S" | awk '/^[^[:space:]]/{print $1; exit}')"
        fi

        [[ -n "$OUT" ]] && break
        sleep 0.1
    done

    if [[ -n "$OUT" ]]; then
        # wlroots transform "90" = 90 degrees clockwise.
        wlr-randr --output "$OUT" --transform 90 >/tmp/matthew-display.log 2>&1 || true
    else
        echo "Matthew: no display output found for rotation" >/tmp/matthew-display.log
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
