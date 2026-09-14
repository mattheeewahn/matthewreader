#!/bin/bash
set -euo pipefail

CONFIG=/boot/firmware/config.txt
CMDLINE=/boot/firmware/cmdline.txt
OVERLAY=vc4-kms-dsi-ili9881-7inch

[[ -f "$CONFIG" ]] || {
    echo "Matthew: $CONFIG not found; skipping portrait cleanup."
    exit 0
}

BACKUP="${CONFIG}.pre-matthew-v5_4-portrait"
if [[ ! -f "$BACKUP" ]]; then
    cp -a "$CONFIG" "$BACKUP"
fi

TMP="$(mktemp)"

# Remove manual Matthew / Touch Display 2 orientation lines from earlier builds.
awk -v overlay="$OVERLAY" '
{
    line=$0
    trimmed=line
    sub(/^[[:space:]]*/, "", trimmed)

    if (trimmed ~ /^# Matthew Reader .*Touch Display/) next
    if (trimmed ~ /^# Matthew Reader v5\.[0-9].*display/) next
    if (trimmed ~ /^# Kernel rotates the panel/) next
    if (trimmed ~ /^# Display output is rotated/) next
    if (trimmed ~ /^# portrait \(x,y\)/) next

    prefix="dtoverlay=" overlay
    if (index(trimmed,prefix)==1) {
        c=substr(trimmed,length(prefix)+1,1)
        if (c=="" || c==",") next
    }

    # We re-add one clean display_auto_detect=1 below.
    if (trimmed ~ /^display_auto_detect=/) next

    print line
}' "$CONFIG" > "$TMP"

cat >>"$TMP" <<'EOF'

# Matthew Reader v5.4 Portrait
# Use the official Touch Display 2 in its native portrait orientation.
# Pi 5 firmware auto-detects the display; no rotation/touch transform is used.
display_auto_detect=1
EOF

cat "$TMP" > "$CONFIG"
rm -f "$TMP"

# Remove orientation-only command-line overrides left by troubleshooting.
if [[ -f "$CMDLINE" ]]; then
    CMD_BACKUP="${CMDLINE}.pre-matthew-v5_4-portrait"
    [[ -f "$CMD_BACKUP" ]] || cp -a "$CMDLINE" "$CMD_BACKUP"

    python3 - "$CMDLINE" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read().strip()
parts = s.split()

clean=[]
for token in parts:
    # Remove DSI rotation overrides added during Matthew troubleshooting.
    if token.startswith("video=DSI-") and "rotate=" in token:
        continue
    if re.fullmatch(r"fbcon=rotate:[0-3]", token):
        continue
    clean.append(token)

open(p, "w", encoding="utf-8").write(" ".join(clean) + "\n")
PY
fi

echo "Matthew v5.4 Portrait:"
echo "  - native portrait display"
echo "  - no wlr-randr transform"
echo "  - no rotation=90"
echo "  - no swapxy/invx/invy"
echo "  - display_auto_detect=1"
