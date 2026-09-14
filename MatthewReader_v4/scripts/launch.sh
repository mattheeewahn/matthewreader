#!/bin/bash
set -u
export QT_QPA_PLATFORM=wayland
if command -v wlr-randr >/dev/null 2>&1; then
  sleep .3
  S="$(wlr-randr 2>/dev/null || true)"
  OUT="$(printf '%s\n' "$S" | awk '/^[^[:space:]].*"/ {print $1; exit}')"
  MODE="$(printf '%s\n' "$S" | awk '/\(.*current.*\)/ {print $1; exit}')"
  if [[ -n "${OUT:-}" && -n "${MODE:-}" ]]; then
    W="${MODE%x*}";H="${MODE#*x}";H="${H%% *}"
    if [[ "$W" =~ ^[0-9]+$ && "$H" =~ ^[0-9]+$ && "$W" -gt "$H" ]]; then
      wlr-randr --output "$OUT" --transform 90 >/dev/null 2>&1 || true
    fi
  fi
fi
if command -v udiskie >/dev/null 2>&1; then
  udiskie --automount --no-notify --no-tray --no-file-manager --no-password-prompt >/tmp/matthew-udiskie.log 2>&1 &
fi
exec /usr/bin/python3 /opt/matthew-reader/run.py
