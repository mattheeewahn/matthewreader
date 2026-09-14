#!/bin/bash
set -euo pipefail

CONFIG=/boot/firmware/config.txt
CMDLINE=/boot/firmware/cmdline.txt
OVERLAY=vc4-kms-dsi-ili9881-7inch

[[ -f "$CONFIG" ]] || {
    echo "Matthew: $CONFIG not found; skipping Touch Display 2 configuration."
    exit 0
}

# Keep a backup before v5.3 changes.
BACKUP="${CONFIG}.pre-matthew-v5_3"
if [[ ! -f "$BACKUP" ]]; then
    cp -a "$CONFIG" "$BACKUP"
fi

# If the user's current explicit panel overlay used dsi0, preserve that bus.
EXISTING="$(grep -E "^[[:space:]]*dtoverlay=${OVERLAY}([,[:space:]]|$)" "$CONFIG" | head -n1 || true)"
BUS=""
if [[ "$EXISTING" == *",dsi0"* ]]; then
    BUS=",dsi0"
fi

TMP="$(mktemp)"

# Remove every prior explicit Touch Display 2 7-inch line. This deliberately
# removes old swapxy/invx/invy and rotation combinations so we do not apply
# two independent coordinate transforms.
awk -v overlay="$OVERLAY" '
{
    line=$0
    trimmed=line
    sub(/^[[:space:]]*/, "", trimmed)

    # Remove old Matthew comments related to display/touch rotation.
    if (trimmed ~ /^# Matthew Reader Touch Display 2 rotation/) next
    if (trimmed ~ /^# Display output is rotated/) next
    if (trimmed ~ /^# portrait \(x,y\)/) next

    prefix="dtoverlay=" overlay
    if (index(trimmed,prefix)==1) {
        c=substr(trimmed,length(prefix)+1,1)
        if (c=="" || c==",") next
    }
    print line
}' "$CONFIG" > "$TMP"

cat >>"$TMP" <<EOF

# Matthew Reader v5.3 - official Touch Display 2
# Kernel rotates the panel and touchscreen together by 90 degrees clockwise.
dtoverlay=${OVERLAY}${BUS},rotation=90
EOF

cat "$TMP" > "$CONFIG"
rm -f "$TMP"

# Remove any DSI-1 rotate= kernel-console argument that may have been added
# during earlier troubleshooting. It is not needed for the DRM/Wayland app
# and keeping one rotation authority avoids ambiguity.
if [[ -f "$CMDLINE" ]]; then
    CMD_BACKUP="${CMDLINE}.pre-matthew-v5_3"
    [[ -f "$CMD_BACKUP" ]] || cp -a "$CMDLINE" "$CMD_BACKUP"
    python3 - "$CMDLINE" <<'PY'
import re, sys
p=sys.argv[1]
s=open(p,encoding="utf-8").read().strip()
parts=s.split()
parts=[x for x in parts if not re.match(r'^video=DSI-1:.*rotate=(0|90|180|270)',x)]
open(p,'w',encoding='utf-8').write(' '.join(parts)+'\n')
PY
fi

echo "Matthew v5.3: using one rotation authority only:"
echo "  dtoverlay=${OVERLAY}${BUS},rotation=90"
echo "Old swapxy/invx/invy and DSI-1 rotate= overrides were removed."
