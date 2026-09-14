#!/bin/bash
set -euo pipefail

CONFIG=/boot/firmware/config.txt
OVERLAY=vc4-kms-dsi-ili9881-7inch

[[ -f "$CONFIG" ]] || {
    echo "Matthew: $CONFIG not found; skipping Touch Display 2 configuration."
    exit 0
}

# Keep one backup of the user's pre-Matthew display configuration.
BACKUP="${CONFIG}.pre-matthew-touch"
if [[ ! -f "$BACKUP" ]]; then
    cp -a "$CONFIG" "$BACKUP"
fi

# Preserve dsi0 if the user's existing explicit overlay uses it.
EXISTING="$(grep -E "^[[:space:]]*dtoverlay=${OVERLAY}([,[:space:]]|$)" "$CONFIG" | head -n1 || true)"
EXTRA=""
if [[ "$EXISTING" == *",dsi0"* ]]; then
    EXTRA=",dsi0"
fi

TMP="$(mktemp)"

# Remove prior explicit Matthew/7-inch Touch Display 2 overlay entries so
# repeated installs are idempotent. Do not touch unrelated overlays.
awk -v overlay="$OVERLAY" '
BEGIN { skip_comment=0 }
/^[[:space:]]*# Matthew Reader Touch Display 2 rotation/ {
    next
}
{
    line=$0
    trimmed=line
    sub(/^[[:space:]]*/, "", trimmed)
    prefix="dtoverlay=" overlay
    if (index(trimmed,prefix)==1) {
        rest=substr(trimmed,length(prefix)+1,1)
        if (rest=="" || rest==",") next
    }
    print line
}' "$CONFIG" > "$TMP"

cat >>"$TMP" <<EOF

# Matthew Reader Touch Display 2 rotation - 90 degrees clockwise
# Display output is rotated by Cage/wlr-randr; touch is mapped to match:
# portrait (x,y) -> landscape (1280-y,x)
dtoverlay=${OVERLAY}${EXTRA},swapxy,invx
EOF

cat "$TMP" > "$CONFIG"
rm -f "$TMP"

echo "Matthew: Touch Display 2 configured for 90-degree clockwise touch mapping."
echo "Matthew: original config backup: $BACKUP"
